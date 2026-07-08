"""
SkillComposer - 技能组合引擎
核心模块：执行组合，生成差异补丁，冲突决策
支持 diff / temp / persist / dry-run 四种输出模式
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

from ..models import (
    ComparisonResult,
    CompositionPlan,
    ConflictOption,
    DiffManifest,
    EvolutionStep,
    ProgressiveInjectionPlan,
    SixDimensionReport,
    SkillMeta,
)
from .pattern_library import PatternLibrary
from .security_guard import SecurityGuard
from .skill_analyzer import SkillAnalyzer
from .skill_loader import SkillLoader
from .skill_parser import SkillParser


class SkillComposer:
    """技能组合引擎"""

    def __init__(
        self,
        loader: SkillLoader,
        parser: SkillParser,
        analyzer: SkillAnalyzer,
        security: SecurityGuard,
        composed_skills_dir: str = "./composed_skills",
        conflict_rules: list[tuple[set[str], str]] | None = None,
    ):
        self._loader = loader
        self._parser = parser
        self._analyzer = analyzer
        self._security = security
        self._composed_dir = Path(os.path.expanduser(composed_skills_dir))
        # 技术栈互斥规则：(互斥集合, 标签) — 用于冲突检测
        self._conflict_rules = conflict_rules or [
            ({"selenium", "playwright"}, "浏览器自动化"),
            ({"requests", "httpx", "aiohttp"}, "HTTP 客户端"),
        ]

    def load_skill(self, skill_name: str) -> SkillMeta:
        """加载并解析一个技能"""
        skill_md_path = self._loader.get_skill_md_path(skill_name)
        if skill_md_path is None:
            raise FileNotFoundError(f"未找到技能: {skill_name}")

        # 安全校验
        self._security.resolve_path(skill_md_path)

        file_hash = self._loader.get_skill_hash(skill_name)
        return self._parser.parse_file(skill_md_path, file_hash)

    def compose(
        self,
        base: str,
        additions: list[str],
        output_mode: str = "diff",
        dry_run: bool = False,
        conflict_choices: dict[str, str] | None = None,
    ) -> CompositionPlan:
        """
        执行技能组合。

        Args:
            base: 基础技能名称
            additions: 要融合的技能列表
            output_mode: diff / temp / persist
            dry_run: 是否仅预演（不生成文件）
            conflict_choices: 冲突决策 {"冲突描述": "A"/"B"/"C"}

        Returns:
            CompositionPlan: 组合方案
        """
        if conflict_choices is None:
            conflict_choices = {}

        # 1. 加载所有技能并校验哈希
        logger.info(f"开始组合: base={base}, additions={additions}")
        base_skill = self.load_skill(base)
        source_hashes = {base_skill.name: base_skill.hash}

        addition_skills: list[SkillMeta] = []
        for name in additions:
            skill = self.load_skill(name)
            addition_skills.append(skill)
            source_hashes[skill.name] = skill.hash

        # 2. 沙箱校验已在各 load_skill 中完成

        # 3. 逐个对比分析
        comparisons: list[ComparisonResult] = []
        modules_to_merge: list[dict] = []
        all_new_deps: list[str] = []

        for cand in addition_skills:
            result = self._analyzer.compare(base_skill, cand)
            comparisons.append(result)

            # 收集候选技能独有的模块
            for mod_name in result.unique_to_candidate:
                cand_mod = None
                for m in cand.modules:
                    if m.name == mod_name:
                        cand_mod = m
                        break
                if cand_mod:
                    modules_to_merge.append(
                        {
                            "name": mod_name,
                            "source": cand.name,
                            "reason": "候选技能独有模块",
                            "content": cand_mod.raw_content,
                            "dependencies": cand_mod.dependencies,
                        }
                    )

            # 收集改进的模块
            for improved in result.improved_in_candidate:
                mod_name = improved.get("module", "")
                if mod_name in ("design_patterns", "tech_stack"):
                    continue
                # 查找候选模块内容
                for m in cand.modules:
                    if m.name == mod_name:
                        modules_to_merge.append(
                            {
                                "name": mod_name,
                                "source": cand.name,
                                "reason": improved.get("reason", "候选技能改进"),
                                "content": m.raw_content,
                                "dependencies": m.dependencies,
                                "replaces": True,
                            }
                        )
                        break

            # 收集新依赖
            for dep in cand.tech_stack:
                if dep not in base_skill.tech_stack and dep not in all_new_deps:
                    all_new_deps.append(dep)

        # 4. 冲突检测
        conflicts = self._detect_conflicts(base_skill, addition_skills, modules_to_merge)

        # 5. 生成差异清单
        diff_manifest = self._generate_diff_manifest(
            base_skill, modules_to_merge, all_new_deps, conflicts
        )

        # dry-run 模式：仅返回报告
        if dry_run:
            logger.info("dry-run 模式，不生成文件")
            return CompositionPlan(
                base_skill=base_skill.name,
                added_skills=[s.name for s in addition_skills],
                modules_to_merge=modules_to_merge,
                new_dependencies=all_new_deps,
                conflicts=conflicts,
                diff_manifest=diff_manifest,
                composed_content=None,
                output_mode="dry-run",
                source_hashes=source_hashes,
            )

        # diff 模式：仅返回差异清单
        if output_mode == "diff":
            logger.info("diff 模式，返回差异清单")
            return CompositionPlan(
                base_skill=base_skill.name,
                added_skills=[s.name for s in addition_skills],
                modules_to_merge=modules_to_merge,
                new_dependencies=all_new_deps,
                conflicts=conflicts,
                diff_manifest=diff_manifest,
                composed_content=None,
                output_mode="diff",
                source_hashes=source_hashes,
            )

        # 6. temp / persist 模式：生成完整内容
        composed_content = self._generate_composed_content(
            base_skill, addition_skills, modules_to_merge, conflicts, conflict_choices
        )

        plan = CompositionPlan(
            base_skill=base_skill.name,
            added_skills=[s.name for s in addition_skills],
            modules_to_merge=modules_to_merge,
            new_dependencies=all_new_deps,
            conflicts=conflicts,
            diff_manifest=diff_manifest,
            composed_content=composed_content,
            output_mode=output_mode,
            source_hashes=source_hashes,
        )

        # persist 模式：保存到隔离目录
        if output_mode == "persist":
            saved_path = self._save_composed_skill(plan)
            plan.saved_path = saved_path

        return plan

    def progressive_inject(
        self,
        base: str,
        source: str,
        output_mode: str = "diff",
        step_filter: list[str] | None = None,
    ) -> ProgressiveInjectionPlan:
        """
        渐进式注入：每次注入一个维度，逐步将 source 技能的能力注入 base。
        支持六维依次注入：speed → accuracy → robustness → output_quality → prompt_strategy → tool_usage

        Args:
            base: 基础技能名称
            source: 源技能名称（从中提取维度增强）
            output_mode: diff / temp / persist
            step_filter: 仅执行指定维度列表（可选）

        Returns:
            ProgressiveInjectionPlan: 渐进式注入计划
        """
        logger.info(f"渐进式注入: base={base}, source={source}")

        dimension_order = [
            "speed",
            "accuracy",
            "robustness",
            "output_quality",
            "prompt_strategy",
            "tool_usage",
        ]

        dimension_labels = {
            "speed": "速度优化",
            "accuracy": "准确度增强",
            "robustness": "鲁棒性强化",
            "output_quality": "输出质量提升",
            "prompt_strategy": "提示策略优化",
            "tool_usage": "工具使用增强",
        }

        base_skill = self.load_skill(base)
        source_skill = self.load_skill(source)

        # 对两个技能进行六维分析
        base_six = self._analyzer._six_dimension_analysis(base_skill)
        source_six = self._analyzer._six_dimension_analysis(source_skill)

        base_radar = base_six.radar
        source_radar = source_six.radar

        steps: list[EvolutionStep] = []

        for dim in dimension_order:
            if step_filter and dim not in step_filter:
                continue

            base_score = base_radar.get(dim, 0)
            source_score = source_radar.get(dim, 0)

            # 只有当源技能在这个维度上有显著优势时才注入
            if source_score <= base_score + 1.0:
                steps.append(
                    EvolutionStep(
                        dimension=dim,
                        status="skipped",
                        sandbox_result=f"源技能在 '{dimension_labels.get(dim, dim)}' 维度无显著优势 "
                        f"(源 {source_score} vs 基础 {base_score})",
                    )
                )
                continue

            # 找出源技能在这个维度相关的模块
            dim_modules = self._find_dimension_modules(
                source_skill, dim
            )

            # 执行沙箱测试：静态兼容性分析
            sandbox_report = self._sandbox_test(base_skill, dim_modules, dim)

            steps.append(
                EvolutionStep(
                    dimension=dim,
                    status="sandboxing",
                    sandbox_result=sandbox_report,
                    merged_modules=[m.name for m in dim_modules],
                )
            )

        return ProgressiveInjectionPlan(
            base_skill=base_skill.name,
            source_skill=source_skill.name,
            steps=steps,
            current_step=0,
            status="draft",
            output_mode=output_mode,
        )

    def _find_dimension_modules(
        self, skill: SkillMeta, dimension: str
    ) -> list:
        """查找技能中与指定维度相关的模块"""
        all_kw = self._analyzer.get_dimension_keywords(dimension)
        if not all_kw:
            return []

        matched: list = []
        for mod in skill.modules:
            combined = (
                (mod.raw_content or "").lower()
                + " "
                + (mod.description or "").lower()
                + " "
                + mod.name.lower()
            )
            if any(kw in combined for kw in all_kw):
                matched.append(mod)

        return matched

    def _sandbox_test(
        self, base: SkillMeta, added_modules: list, dimension: str
    ) -> str:
        """
        沙箱测试：模拟将模块注入基础技能后的影响分析。
        返回测试报告（非执行性沙箱，而是静态兼容性分析）。
        """
        issues: list[str] = []

        # 1. 依赖冲突检查
        base_deps = set(base.tech_stack)
        for mod in added_modules:
            for dep in mod.dependencies or []:
                if dep not in base_deps:
                    issues.append(f"新依赖: {dep}（需要安装）")

        # 2. 模块名冲突检查
        base_names = {m.name for m in base.modules}
        for mod in added_modules:
            if mod.name in base_names:
                issues.append(f"模块名冲突: '{mod.name}' 已存在")

        # 3. 维度评分预期变化
        if not issues:
            return f"沙箱测试通过：{dimension} 维度注入 {len(added_modules)} 个模块，无冲突"
        else:
            return (
                f"沙箱测试报告（{dimension}）：\n"
                + "\n".join(f"  - {issue}" for issue in issues)
            )

    def approve_step(
        self, plan: ProgressiveInjectionPlan, step_index: int
    ) -> ProgressiveInjectionPlan:
        """批准某个渐进式注入步骤"""
        if step_index >= len(plan.steps):
            raise ValueError(f"步骤索引超出范围: {step_index} >= {len(plan.steps)}")

        step = plan.steps[step_index]
        if step.status != "sandboxing":
            raise ValueError(f"步骤 {step_index} 状态不是 sandboxing: {step.status}")

        step.status = "approved"
        plan.current_step = step_index + 1

        # 检查是否所有步骤都完成
        if all(s.status in ("approved", "skipped") for s in plan.steps):
            plan.status = "completed"

        return plan

    def reject_step(
        self, plan: ProgressiveInjectionPlan, step_index: int
    ) -> ProgressiveInjectionPlan:
        """拒绝某个渐进式注入步骤"""
        if step_index >= len(plan.steps):
            raise ValueError(f"步骤索引超出范围: {step_index} >= {len(plan.steps)}")

        step = plan.steps[step_index]
        step.status = "rejected"
        plan.current_step = step_index + 1

        # 检查是否所有步骤都完成
        if all(s.status in ("approved", "rejected", "skipped") for s in plan.steps):
            plan.status = "completed"

        return plan

    def _detect_conflicts(
        self,
        base: SkillMeta,
        additions: list[SkillMeta],
        modules_to_merge: list[dict],
    ) -> list[ConflictOption]:
        """检测冲突"""
        conflicts: list[ConflictOption] = []

        # 检测模块名冲突（要替换的模块在多个候选中都存在）
        replace_modules: dict[str, list[str]] = {}
        for mod in modules_to_merge:
            if mod.get("replaces"):
                name = mod["name"]
                source = mod["source"]
                if name not in replace_modules:
                    replace_modules[name] = []
                replace_modules[name].append(source)

        for mod_name, sources in replace_modules.items():
            if len(sources) > 1:
                conflicts.append(
                    ConflictOption(
                        conflict=f"模块 '{mod_name}' 在多个候选技能中都存在: {', '.join(sources)}",
                        module=mod_name,
                        options=[
                            f"A: 使用基础技能 '{base.name}' 的 {mod_name}",
                            f"B: 使用第一个候选 '{sources[0]}' 的 {mod_name}",
                            "C: 合并所有版本（需手动编辑）",
                        ],
                        default_choice="A",
                    )
                )

        # 检测技术栈冲突（不同技能使用不同实现方式）
        base_stack = set(base.tech_stack)
        for cand in additions:
            # 检测互斥技术栈（规则来自构造参数 self._conflict_rules）
            for exclusive_set, label in self._conflict_rules:
                base_match = base_stack & exclusive_set
                cand_match = set(cand.tech_stack) & exclusive_set
                if base_match and cand_match and base_match != cand_match:
                    conflict_desc = f"技术栈冲突（{label}）: 基础用 {base_match}，候选 '{cand.name}' 用 {cand_match}"
                    # 避免重复
                    if not any(c.conflict == conflict_desc for c in conflicts):
                        conflicts.append(
                            ConflictOption(
                                conflict=conflict_desc,
                                module="tech_stack",
                                options=[
                                    f"A: 保留基础技能的 {base_match}",
                                    f"B: 使用候选技能的 {cand_match}",
                                    "C: 两者都保留（可能需要手动适配）",
                                ],
                                default_choice="A",
                            )
                        )

        # 检测设计模式冲突（如双重等待策略）
        base_patterns = set(base.design_patterns)
        for cand in additions:
            cand_patterns = set(cand.design_patterns)
            # 如果两个技能都有"重试策略"但实现可能不同
            common_patterns = base_patterns & cand_patterns
            for pattern in common_patterns:
                if pattern in ("重试策略", "缓存策略", "并发控制"):
                    conflict_desc = f"设计模式冲突: '{pattern}' 在基础和候选 '{cand.name}' 中都存在"
                    if not any(c.conflict == conflict_desc for c in conflicts):
                        conflicts.append(
                            ConflictOption(
                                conflict=conflict_desc,
                                module=pattern,
                                options=[
                                    f"A: 使用基础技能的 {pattern}",
                                    f"B: 使用候选 '{cand.name}' 的 {pattern}",
                                    "C: 合并两者策略",
                                ],
                                default_choice="A",
                            )
                        )

        return conflicts

    def _generate_diff_manifest(
        self,
        base: SkillMeta,
        modules_to_merge: list[dict],
        new_deps: list[str],
        conflicts: list[ConflictOption],
    ) -> DiffManifest:
        """生成结构化差异清单"""
        added: list[dict[str, str]] = []
        modified: list[dict[str, str]] = []
        removed: list[dict[str, str]] = []

        for mod in modules_to_merge:
            if mod.get("replaces"):
                modified.append(
                    {
                        "module": mod["name"],
                        "source": mod["source"],
                        "reason": mod["reason"],
                    }
                )
            else:
                added.append(
                    {
                        "module": mod["name"],
                        "source": mod["source"],
                        "reason": mod["reason"],
                    }
                )

        return DiffManifest(
            added_modules=added,
            removed_modules=removed,
            modified_modules=modified,
            new_dependencies=new_deps,
            conflict_options=conflicts,
        )

    def _generate_composed_content(
        self,
        base: SkillMeta,
        additions: list[SkillMeta],
        modules_to_merge: list[dict],
        conflicts: list[ConflictOption],
        conflict_choices: dict[str, str],
    ) -> str:
        """生成组合后的完整 SKILL.md 内容"""
        lines: list[str] = []

        # 生成 Frontmatter
        lines.append("---")
        lines.append(f"name: {base.name}+{'+'.join(a.name for a in additions)}")
        lines.append(
            f"description: 组合技能 - 基础: {base.name}, 融合: {', '.join(a.name for a in additions)}"
        )
        lines.append("version: 2.0.0")
        lines.append("author: skill-composer-mcp")
        lines.append(f"composed_at: {datetime.now().isoformat()}")
        lines.append(f"source_hashes:")
        for name, h in [(base.name, base.hash)] + [(a.name, a.hash) for a in additions]:
            lines.append(f"  {name}: {h}")
        lines.append("---")
        lines.append("")

        # 标题
        combined_name = f"{base.name} + {' + '.join(a.name for a in additions)}"
        lines.append(f"# {combined_name}")
        lines.append("")
        lines.append(f"> 本技能由 skill-composer-mcp 自动组合生成")
        lines.append(f"> 基础技能: {base.name}")
        lines.append(f"> 融合技能: {', '.join(a.name for a in additions)}")
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 保留基础技能原始内容（去除已有的 Frontmatter）
        base_content = base.raw_content
        if base_content.startswith("---"):
            # 去除 frontmatter
            parts = base_content.split("---", 2)
            if len(parts) >= 3:
                base_content = parts[2].strip()

        lines.append(base_content)
        lines.append("")

        # 添加融合模块
        lines.append("---")
        lines.append("")
        lines.append("# 融合模块")
        lines.append("")

        for mod in modules_to_merge:
            # 检查是否有冲突需要处理
            skip = False
            for conflict in conflicts:
                if conflict.module == mod["name"]:
                    choice = conflict_choices.get(conflict.conflict, conflict.default_choice)
                    if choice == "A":
                        skip = True  # 保留基础技能版本
                        lines.append(f"## {mod['name']}（保留基础技能版本）")
                        lines.append("")
                        break

            if skip:
                continue

            lines.append(f"## {mod['name']}")
            lines.append(f"> 来源: {mod['source']} | 原因: {mod['reason']}")
            lines.append("")
            lines.append(mod.get("content", ""))
            lines.append("")

        # 添加新依赖说明
        if modules_to_merge:
            all_deps: list[str] = []
            for mod in modules_to_merge:
                all_deps.extend(mod.get("dependencies", []))
            if all_deps:
                lines.append("---")
                lines.append("")
                lines.append("# 依赖说明")
                lines.append("")
                lines.append("本组合技能可能需要以下依赖：")
                for dep in sorted(set(all_deps)):
                    lines.append(f"- {dep}")
                lines.append("")

        return "\n".join(lines)

    def _save_composed_skill(self, plan: CompositionPlan) -> str:
        """保存组合技能到隔离目录"""
        # 确保隔离目录存在
        self._composed_dir.mkdir(parents=True, exist_ok=True)

        # 生成目录名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        all_names = [plan.base_skill] + plan.added_skills
        dir_name = "+".join(all_names) + f"_{timestamp}"
        target_dir = self._composed_dir / dir_name

        # 安全校验
        self._security.validate_write_target(str(target_dir))

        target_dir.mkdir(parents=True, exist_ok=True)

        # 写入 SKILL.md
        skill_md_path = target_dir / "SKILL.md"
        content = plan.composed_content or ""
        skill_md_path.write_text(content, encoding="utf-8")

        # 写入元数据
        meta_path = target_dir / "composition_meta.json"
        import json
        meta = {
            "base_skill": plan.base_skill,
            "added_skills": plan.added_skills,
            "source_hashes": plan.source_hashes,
            "created_at": datetime.now().isoformat(),
            "output_mode": plan.output_mode,
            "modules_merged": len(plan.modules_to_merge),
            "conflicts": [c.model_dump() for c in plan.conflicts],
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        logger.info(f"组合技能已保存: {target_dir}")
        return str(target_dir)
