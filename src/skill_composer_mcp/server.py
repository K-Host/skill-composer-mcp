"""
MCP Server - 接口层
注册 6 个 MCP 工具，处理协议请求
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from loguru import logger

from .config import AppConfig, ConfigFile, load_config
from .core.llm_factory import LLMFactory
from .core.pattern_library import PatternLibrary
from .core.security_guard import SecurityGuard
from .core.skill_analyzer import SkillAnalyzer
from .core.skill_composer import SkillComposer
from .core.skill_loader import SkillLoader
from .core.skill_parser import SkillParser
from .core.template_manager import TemplateManager
from .models import CompositionPlan, ProgressiveInjectionPlan
from .utils.fuzzy_matcher import FuzzyMatcher


SETUP_PROMPT = """## 🔧 首次使用 - 请配置技能目录

还没有配置技能路径。请使用 `configure_skills` 工具指定技能文件所在目录。

用法示例：
- **opencode 内置技能**: `~/.config/opencode/skills`
- **项目自定义技能**: `./skills` 或 `./examples/skills`
- **多个目录**: 传入列表即可

调用 `configure_skills` 后配置会保存到 `~/.skill-composer/config.yaml`，
后续修改该文件会自动热加载，无需重启服务。
"""


class SkillComposerServer:
    """MCP Server - 技能组合器"""

    def __init__(self, config: AppConfig | None = None):
        self._config_file = ConfigFile()
        self._config = config or load_config(self._config_file)
        self._config_mtime: float = 0

        self._init_components()

        logger.info("SkillComposerServer 初始化完成")

    def _init_components(self) -> None:
        """初始化/重新初始化所有核心组件"""
        self._security = SecurityGuard(
            allowed_roots=self._config.security.allowed_roots or self._config.skill_paths,
            forbidden_dirs=self._config.security.forbidden_dirs,
            allow_read_only=self._config.security.allow_read_only,
            composed_skills_dir=self._config.composed_skills_dir,
        )
        self._loader = SkillLoader(
            skill_paths=self._config.skill_paths,
            security_guard=self._security,
        )
        self._parser = SkillParser(
            fallback_to_llm=self._config.parser.fallback_to_llm,
            frontmatter_schema=self._config.parser.frontmatter_schema,
        )
        self._analyzer = SkillAnalyzer()
        self._composer = SkillComposer(
            loader=self._loader,
            parser=self._parser,
            analyzer=self._analyzer,
            security=self._security,
            composed_skills_dir=self._config.composed_skills_dir,
        )
        self._template_mgr = TemplateManager()
        self._pattern_lib = PatternLibrary(
            storage_path=self._config.pattern_library_path
        )
        self._fuzzy = FuzzyMatcher()

    def _hot_reload(self) -> bool:
        """
        检测配置文件变更并热加载。
        在每次工具调用前调用，若文件已变更则重新加载配置和组件。
        返回 True 表示发生了热加载。
        """
        if not self._config_file.changed_since(self._config_mtime):
            return False

        logger.info("检测到配置文件变更，执行热加载...")
        old_paths = list(self._config.skill_paths)
        self._config = load_config(self._config_file)
        self._config_mtime = self._config_file._get_mtime()
        self._init_components()
        logger.info(f"热加载完成: skill_paths 从 {old_paths} -> {self._config.skill_paths}")
        return True

    # ==================== MCP Tools ====================

    async def tool_list_skills(self, query: str | None = None) -> str:
        """
        Tool 1: list_skills
        列出所有本地技能（支持模糊搜索）

        Args:
            query: 搜索关键词（可选）

        Returns:
            技能列表 JSON
        """
        self._hot_reload()

        # 首次使用引导
        if not self._config.skill_paths:
            return json.dumps(
                {
                    "message": "未配置技能目录",
                    "setup_required": True,
                    "setup_hint": SETUP_PROMPT,
                    "available_tools": [
                        "configure_skills - 配置技能目录路径",
                        "reload_config  - 重新加载配置文件",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )

        skills = self._loader.list_skills(include_description=bool(query))

        if not skills:
            return json.dumps(
                {"message": "未找到任何技能", "skill_paths": self._loader.skill_paths},
                ensure_ascii=False,
                indent=2,
            )

        if query:
            results = self._fuzzy.search(
                query=query,
                candidates=skills,
                key_fields=["name", "description"],
                limit=10,
                min_score=30,
            )
            return json.dumps(
                {
                    "query": query,
                    "count": len(results),
                    "skills": results,
                },
                ensure_ascii=False,
                indent=2,
            )

        return json.dumps(
            {"count": len(skills), "skills": skills},
            ensure_ascii=False,
            indent=2,
        )

    async def tool_analyze_skill(self, skill_name: str) -> str:
        """
        Tool 2: analyze_skill
        深度分析指定技能

        Args:
            skill_name: 技能名称

        Returns:
            技能分析报告 JSON
        """
        self._hot_reload()
        if not self._config.skill_paths:
            return json.dumps({"error": "未配置技能目录，请先调用 configure_skills"}, ensure_ascii=False, indent=2)
        try:
            skill = self._composer.load_skill(skill_name)
            report = self._analyzer.analyze(skill)
            return json.dumps(report, ensure_ascii=False, indent=2)
        except FileNotFoundError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"分析技能失败: {e}")
            return json.dumps({"error": f"分析失败: {e}"}, ensure_ascii=False, indent=2)

    async def tool_compare_skills(
        self, base_skill: str, candidate_skill: str
    ) -> str:
        """
        Tool 3: compare_skills
        对比两个技能的差异

        Args:
            base_skill: 基础技能名称
            candidate_skill: 候选技能名称

        Returns:
            对比结果 JSON
        """
        self._hot_reload()
        if not self._config.skill_paths:
            return json.dumps({"error": "未配置技能目录，请先调用 configure_skills"}, ensure_ascii=False, indent=2)
        try:
            base = self._composer.load_skill(base_skill)
            candidate = self._composer.load_skill(candidate_skill)
            result = self._analyzer.compare(base, candidate)
            return json.dumps(
                result.model_dump(), ensure_ascii=False, indent=2
            )
        except FileNotFoundError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"对比技能失败: {e}")
            return json.dumps({"error": f"对比失败: {e}"}, ensure_ascii=False, indent=2)

    async def tool_compose_skills(
        self,
        base: str,
        additions: list[str],
        output_mode: str | None = None,
        dry_run: bool = False,
        conflict_choices: dict[str, str] | None = None,
    ) -> str:
        """
        Tool 4: compose_skills
        组合多个技能（支持 diff/dry-run/temp/persist）

        Args:
            base: 基础技能名称
            additions: 要融合的技能列表
            output_mode: 输出模式 (diff/temp/persist)，默认从配置读取
            dry_run: 是否仅预演
            conflict_choices: 冲突决策

        Returns:
            组合方案 JSON
        """
        self._hot_reload()
        if not self._config.skill_paths:
            return json.dumps({"error": "未配置技能目录，请先调用 configure_skills"}, ensure_ascii=False, indent=2)
        if output_mode is None:
            output_mode = self._config.output.default_mode

        try:
            plan = self._composer.compose(
                base=base,
                additions=additions,
                output_mode=output_mode,
                dry_run=dry_run,
                conflict_choices=conflict_choices,
            )

            result = plan.model_dump()

            # 对于 diff/dry-run 模式，不返回完整内容
            if plan.output_mode in ("diff", "dry-run"):
                result["composed_content"] = None
                result["message"] = (
                    f"{'预演' if dry_run else '差异'}模式：请查看 diff_manifest，"
                    f"确认后可用 output_mode='temp' 或 'persist' 生成完整内容"
                )
            elif plan.output_mode == "temp":
                result["message"] = "临时模式：组合内容已生成，未保存到磁盘"
            elif plan.output_mode == "persist":
                result["message"] = f"持久模式：组合技能已保存到 {plan.saved_path}"

            return json.dumps(result, ensure_ascii=False, indent=2)
        except FileNotFoundError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"组合技能失败: {e}")
            return json.dumps({"error": f"组合失败: {e}"}, ensure_ascii=False, indent=2)

    async def tool_recommend_combo(
        self, task: str, llm_provider: str | None = None
    ) -> str:
        """
        Tool 5: recommend_combo
        根据任务描述自动推荐最佳组合

        Args:
            task: 任务描述
            llm_provider: LLM 提供商（可选，默认从配置读取）

        Returns:
            推荐方案 JSON
        """
        self._hot_reload()
        if not self._config.skill_paths:
            return json.dumps({"error": "未配置技能目录，请先调用 configure_skills"}, ensure_ascii=False, indent=2)
        provider = llm_provider or self._config.llm.provider
        skills = self._loader.list_skills()

        if not skills:
            return json.dumps(
                {"error": "未找到任何技能，无法推荐"}, ensure_ascii=False, indent=2
            )

        # 构建技能列表摘要
        skill_summaries = [
            f"- {s['name']}: {s.get('path', '')}" for s in skills
        ]

        # 使用 LLM 推荐
        llm = LLMFactory.create(
            provider=provider,
            api_key=self._config.llm.api_key,
            model=self._config.llm.model,
            base_url=self._config.llm.base_url,
        )

        prompt = f"""请根据以下任务描述，从可用技能列表中推荐最佳组合方案。

任务描述：{task}

可用技能列表：
{chr(10).join(skill_summaries)}

请返回 JSON 格式：
{{
  "base_skill": "推荐的基础技能名",
  "additions": ["推荐融合的技能名列表"],
  "reason": "推荐理由",
  "output_mode": "建议的输出模式(diff/temp/persist)"
}}

只返回 JSON，不要其他内容。
"""

        system_prompt = "你是一个技能组合推荐专家，帮助用户选择最合适的技能组合。"

        try:
            llm_response = await llm.chat(prompt, system=system_prompt)

            # 尝试解析 LLM 返回的 JSON
            try:
                # 提取 JSON 部分
                json_str = llm_response
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0]

                recommendation = json.loads(json_str.strip())
            except json.JSONDecodeError:
                # 如果 LLM 返回的不是有效 JSON，使用规则引擎
                recommendation = self._rule_based_recommend(task, skills)

            recommendation["llm_provider"] = provider
            return json.dumps(recommendation, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"LLM 推荐失败: {e}，使用规则引擎")
            recommendation = self._rule_based_recommend(task, skills)
            recommendation["llm_provider"] = f"rule_engine (LLM failed: {e})"
            return json.dumps(recommendation, ensure_ascii=False, indent=2)

    def _rule_based_recommend(self, task: str, skills: list[dict]) -> dict:
        """规则引擎推荐（LLM 不可用时的回退）"""
        task_lower = task.lower()

        # 基于关键词匹配
        scored: list[tuple[dict, int]] = []
        for skill in skills:
            score = 0
            name = skill["name"].lower()
            # 名称匹配
            for word in task_lower.split():
                if word in name:
                    score += 10
            # 模糊匹配
            fuzzy_result = self._fuzzy.search(
                query=task,
                candidates=[skill],
                key_fields=["name"],
                min_score=0,
            )
            if fuzzy_result:
                score += fuzzy_result[0].get("score", 0) // 5

            scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        if not scored or scored[0][1] == 0:
            return {
                "base_skill": skills[0]["name"] if skills else "",
                "additions": [],
                "reason": "无法精确匹配，默认推荐第一个技能",
                "output_mode": "diff",
            }

        base = scored[0][0]
        additions = [s[0]["name"] for s in scored[1:3] if s[1] > 0]

        return {
            "base_skill": base["name"],
            "additions": additions,
            "reason": f"基于关键词匹配，'{base['name']}' 与任务最相关",
            "output_mode": "diff",
        }

    async def tool_save_template(
        self,
        template_name: str,
        base_skill: str,
        additions: list[str],
        description: str = "",
    ) -> str:
        """
        Tool 6a: save_template
        保存组合模板

        Args:
            template_name: 模板名称
            base_skill: 基础技能
            additions: 融合技能列表
            description: 模板描述

        Returns:
            保存结果 JSON
        """
        template = self._template_mgr.save_template(
            name=template_name,
            base_skill=base_skill,
            additions=additions,
            description=description,
        )
        # 手动序列化 datetime
        template_dict = template.model_dump()
        template_dict["created_at"] = template_dict["created_at"].isoformat()
        return json.dumps(
            {"message": "模板已保存", "template": template_dict},
            ensure_ascii=False,
            indent=2,
        )

    async def tool_load_template(self, template_name: str) -> str:
        """
        Tool 6b: load_template
        加载组合模板

        Args:
            template_name: 模板名称

        Returns:
            模板内容 JSON
        """
        template = self._template_mgr.load_template(template_name)
        if template is None:
            available = self._template_mgr.list_templates()
            return json.dumps(
                {
                    "error": f"模板 '{template_name}' 不存在",
                    "available_templates": [t["name"] for t in available],
                },
                ensure_ascii=False,
                indent=2,
            )
        template_dict = template.model_dump()
        template_dict["created_at"] = template_dict["created_at"].isoformat()
        return json.dumps(
            {"template": template_dict},
            ensure_ascii=False,
            indent=2,
        )

    async def tool_list_templates(self) -> str:
        """列出所有模板"""
        templates = self._template_mgr.list_templates()
        return json.dumps(
            {"count": len(templates), "templates": templates},
            ensure_ascii=False,
            indent=2,
        )

    async def tool_configure_skills(self, skill_paths: list[str]) -> str:
        """
        Tool 7: configure_skills
        配置技能目录路径。保存到配置文件后自动热加载。

        Args:
            skill_paths: 技能目录路径列表，例如 ["~/.config/opencode/skills", "./skills"]

        Returns:
            配置结果 JSON
        """
        # 展开 ~ 路径
        expanded = []
        for p in skill_paths:
            expanded.append(os.path.expanduser(p))
        self._config_file.save({"skill_paths": expanded})
        # 立即热加载
        self._config = load_config(self._config_file)
        self._config_mtime = self._config_file._get_mtime()
        self._init_components()
        return json.dumps(
            {
                "message": "配置已保存并加载",
                "config_path": str(self._config_file.path),
                "skill_paths": expanded,
                "skill_count": len(self._loader.list_skills()),
            },
            ensure_ascii=False,
            indent=2,
        )

    async def tool_reload_config(self) -> str:
        """
        Tool 8: reload_config
        重新加载配置文件（热加载），适用于手动修改配置文件后同步。

        Returns:
            重载结果 JSON
        """
        old_paths = list(self._config.skill_paths)
        self._config = load_config(self._config_file)
        self._config_mtime = self._config_file._get_mtime()
        self._init_components()
        return json.dumps(
            {
                "message": "配置已重新加载",
                "config_path": str(self._config_file.path),
                "old_skill_paths": old_paths,
                "new_skill_paths": self._config.skill_paths,
                "skill_count": len(self._loader.list_skills()),
            },
            ensure_ascii=False,
            indent=2,
        )

    async def tool_search_patterns(
        self,
        query: str = "",
        category: str = "",
        tags: list[str] | None = None,
        min_success_rate: float = 0.0,
        limit: int = 20,
    ) -> str:
        """
        Tool 9: search_patterns
        搜索模式库。从已分析技能中提取的复用模式支持搜索、分类和成功率追踪。

        Args:
            query: 搜索关键词
            category: 按分类筛选 (prompt_design / error_handling / performance / ...)
            tags: 按标签筛选
            min_success_rate: 最低成功率 (0-100)
            limit: 返回条数上限

        Returns:
            模式列表 JSON
        """
        results = self._pattern_lib.search(
            query=query,
            category=category,
            tags=tags,
            min_success_rate=min_success_rate,
            limit=limit,
        )
        stats = self._pattern_lib.get_statistics()
        return json.dumps(
            {
                "count": len(results),
                "patterns": results,
                "statistics": stats,
            },
            ensure_ascii=False,
            indent=2,
        )

    async def tool_analyze_evolution(
        self,
        base_skill: str,
        source_skill: str,
        include_pattern_extraction: bool = True,
    ) -> str:
        """
        Tool 10: analyze_evolution
        逆向进化分析：对比两个技能的六维评分差异，生成逐步进化路线图。
        自动从源技能提取模式存入模式库。

        Args:
            base_skill: 当前技能名称
            source_skill: 目标进化技能名称
            include_pattern_extraction: 是否自动提取模式入库

        Returns:
            进化分析报告 JSON
        """
        self._hot_reload()
        try:
            base = self._composer.load_skill(base_skill)
            source = self._composer.load_skill(source_skill)

            base_six = self._analyzer._six_dimension_analysis(base)
            source_six = self._analyzer._six_dimension_analysis(source)

            # 维度差异
            dimension_diffs: list[dict] = []
            all_dims = ["speed", "accuracy", "robustness", "output_quality", "prompt_strategy", "tool_usage"]
            dim_labels = {
                "speed": "速度", "accuracy": "准确度", "robustness": "鲁棒性",
                "output_quality": "输出质量", "prompt_strategy": "提示策略", "tool_usage": "工具使用",
            }

            for dim in all_dims:
                base_score = base_six.radar.get(dim, 0)
                source_score = source_six.radar.get(dim, 0)
                diff = round(source_score - base_score, 1)
                dimension_diffs.append({
                    "dimension": dim,
                    "label": dim_labels.get(dim, dim),
                    "base_score": base_score,
                    "source_score": source_score,
                    "diff": diff,
                    "improvement_needed": diff > 0,
                })

            # 渐进式注入路线图
            roadmap_steps = [
                d for d in dimension_diffs if d["improvement_needed"]
            ]
            roadmap_steps.sort(key=lambda d: d["source_score"] - d["base_score"], reverse=True)

            # 自动提取模式
            extracted_patterns = []
            if include_pattern_extraction:
                extracted = self._pattern_lib.auto_extract_from_skill(
                    skill_name=source_skill,
                    description=source.description,
                    tech_stack=source.tech_stack,
                    modules=source.modules,
                )
                extracted_patterns = [
                    {"name": e.name, "category": e.category, "tags": e.tags}
                    for e in extracted
                ]

            return json.dumps(
                {
                    "base_skill": base_skill,
                    "source_skill": source_skill,
                    "base_six_radar": base_six.radar,
                    "source_six_radar": source_six.radar,
                    "dimension_diffs": dimension_diffs,
                    "overall_diff": round(source_six.overall_score - base_six.overall_score, 1),
                    "roadmap": roadmap_steps,
                    "roadmap_summary": (
                        f"从 '{base_skill}' 进化到 '{source_skill}' 需要 {len(roadmap_steps)} 个维度的改进。"
                        f"建议按此顺序：{' → '.join(s['dimension'] for s in roadmap_steps)}"
                    ),
                    "extracted_patterns": extracted_patterns if extracted_patterns else None,
                },
                ensure_ascii=False,
                indent=2,
            )
        except FileNotFoundError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"进化分析失败: {e}")
            return json.dumps({"error": f"进化分析失败: {e}"}, ensure_ascii=False, indent=2)

    async def tool_progressive_inject(
        self,
        base: str,
        source: str,
        output_mode: str = "diff",
        step_filter: list[str] | None = None,
    ) -> str:
        """
        Tool 11: progressive_inject
        渐进式注入：将源技能的维度能力逐步注入基础技能。
        一次一个维度（speed → accuracy → robustness → output_quality → prompt_strategy → tool_usage），
        每个步骤需要用户确认（approve/reject）。

        Args:
            base: 基础技能名称（待增强）
            source: 源技能名称（从中提取维度增强）
            output_mode: 输出模式 (diff/temp/persist)
            step_filter: 仅关注指定维度，例如 ["speed", "robustness"]

        Returns:
            渐进式注入计划 JSON
        """
        self._hot_reload()
        try:
            plan = self._composer.progressive_inject(
                base=base,
                source=source,
                output_mode=output_mode,
                step_filter=step_filter,
            )
            return json.dumps(
                plan.model_dump(),
                ensure_ascii=False,
                indent=2,
            )
        except FileNotFoundError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"渐进式注入失败: {e}")
            return json.dumps({"error": f"渐进式注入失败: {e}"}, ensure_ascii=False, indent=2)

    async def tool_approve_step(
        self,
        plan_json: str,
        step_index: int,
    ) -> str:
        """
        Tool 11b: approve_step
        批准渐进式注入的某个步骤。

        Args:
            plan_json: progressive_inject 返回的完整 JSON
            step_index: 要批准的步骤索引

        Returns:
            更新后的计划 JSON
        """
        import json as _json
        try:
            plan_data = _json.loads(plan_json)
            plan = ProgressiveInjectionPlan(**plan_data)
            plan = self._composer.approve_step(plan, step_index)
            return _json.dumps(
                plan.model_dump(),
                ensure_ascii=False,
                indent=2,
            )
        except Exception as e:
            logger.error(f"批准步骤失败: {e}")
            return json.dumps({"error": f"批准步骤失败: {e}"}, ensure_ascii=False, indent=2)

    async def tool_reject_step(
        self,
        plan_json: str,
        step_index: int,
    ) -> str:
        """
        Tool 11c: reject_step
        拒绝渐进式注入的某个步骤。

        Args:
            plan_json: progressive_inject 返回的完整 JSON
            step_index: 要拒绝的步骤索引

        Returns:
            更新后的计划 JSON
        """
        import json as _json
        try:
            plan_data = _json.loads(plan_json)
            plan = ProgressiveInjectionPlan(**plan_data)
            plan = self._composer.reject_step(plan, step_index)
            return _json.dumps(
                plan.model_dump(),
                ensure_ascii=False,
                indent=2,
            )
        except Exception as e:
            logger.error(f"拒绝步骤失败: {e}")
            return json.dumps({"error": f"拒绝步骤失败: {e}"}, ensure_ascii=False, indent=2)


# ==================== MCP 协议适配 ====================

def get_tool_definitions() -> list[dict]:
    """返回 MCP 工具定义列表"""
    return [
        {
            "name": "list_skills",
            "description": "列出所有本地技能，支持模糊搜索。返回技能名称、路径和哈希。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词（可选，支持模糊匹配）",
                    },
                },
            },
        },
        {
            "name": "analyze_skill",
            "description": "深度分析指定技能。提取能力模块、技术栈、设计模式等。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "技能名称",
                    },
                },
                "required": ["skill_name"],
            },
        },
        {
            "name": "compare_skills",
            "description": "对比两个技能的差异。输出共同能力、独有能力、改进点和建议优先级。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "base_skill": {
                        "type": "string",
                        "description": "基础技能名称",
                    },
                    "candidate_skill": {
                        "type": "string",
                        "description": "候选技能名称",
                    },
                },
                "required": ["base_skill", "candidate_skill"],
            },
        },
        {
            "name": "compose_skills",
            "description": "组合多个技能。支持diff模式（仅差异清单）、temp模式（临时返回）、persist模式（持久保存）、dry-run预演。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "base": {
                        "type": "string",
                        "description": "基础技能名称（作为骨架）",
                    },
                    "additions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要融合的技能列表",
                    },
                    "output_mode": {
                        "type": "string",
                        "enum": ["diff", "temp", "persist"],
                        "description": "输出模式，默认diff",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "是否仅预演（不生成文件）",
                    },
                    "conflict_choices": {
                        "type": "object",
                        "description": "冲突决策，key为冲突描述，value为A/B/C",
                    },
                },
                "required": ["base", "additions"],
            },
        },
        {
            "name": "recommend_combo",
            "description": "根据任务描述自动推荐最佳技能组合。支持本地Ollama模型和云端LLM。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "任务描述",
                    },
                    "llm_provider": {
                        "type": "string",
                        "enum": ["ollama", "openai", "anthropic"],
                        "description": "LLM提供商（可选）",
                    },
                },
                "required": ["task"],
            },
        },
        {
            "name": "save_template",
            "description": "保存常用组合为模板，便于后续一键复用。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template_name": {
                        "type": "string",
                        "description": "模板名称",
                    },
                    "base_skill": {
                        "type": "string",
                        "description": "基础技能",
                    },
                    "additions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "融合技能列表",
                    },
                    "description": {
                        "type": "string",
                        "description": "模板描述",
                    },
                },
                "required": ["template_name", "base_skill", "additions"],
            },
        },
        {
            "name": "load_template",
            "description": "加载已保存的组合模板。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template_name": {
                        "type": "string",
                        "description": "模板名称",
                    },
                },
                "required": ["template_name"],
            },
        },
        {
            "name": "list_templates",
            "description": "列出所有已保存的组合模板。",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "configure_skills",
            "description": "配置技能目录路径。第一次使用时必须调用此工具指定技能文件所在目录。保存后会写入配置文件并自动热加载。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "skill_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "技能目录路径列表，例如 [\"~/.config/opencode/skills\", \"./skills\"]",
                    },
                },
                "required": ["skill_paths"],
            },
        },
        {
            "name": "reload_config",
            "description": "重新加载配置文件（热加载）。适用于手动修改 ~/.skill-composer/config.yaml 后同步到运行中的服务。",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "search_patterns",
            "description": "搜索模式库。从已分析技能中提取的复用模式支持搜索、分类和成功率追踪。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词（可选）",
                    },
                    "category": {
                        "type": "string",
                        "description": "按分类筛选 (prompt_design / error_handling / performance / ...)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "按标签筛选",
                    },
                    "min_success_rate": {
                        "type": "number",
                        "description": "最低成功率 (0-100)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回条数上限",
                    },
                },
            },
        },
        {
            "name": "analyze_evolution",
            "description": "逆向进化分析：对比两个技能的六维评分差异，生成逐步进化路线图。自动从源技能提取模式存入模式库。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "base_skill": {
                        "type": "string",
                        "description": "当前技能名称",
                    },
                    "source_skill": {
                        "type": "string",
                        "description": "目标进化技能名称",
                    },
                    "include_pattern_extraction": {
                        "type": "boolean",
                        "description": "是否自动提取模式入库（默认 true）",
                    },
                },
                "required": ["base_skill", "source_skill"],
            },
        },
        {
            "name": "progressive_inject",
            "description": "渐进式注入：将源技能的维度能力逐步注入基础技能。一次一个维度，每个步骤需要用户确认（approve/reject）。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "base": {
                        "type": "string",
                        "description": "基础技能名称（待增强）",
                    },
                    "source": {
                        "type": "string",
                        "description": "源技能名称（从中提取维度增强）",
                    },
                    "output_mode": {
                        "type": "string",
                        "enum": ["diff", "temp", "persist"],
                        "description": "输出模式，默认 diff",
                    },
                    "step_filter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "仅关注指定维度，例如 [\"speed\", \"robustness\"]",
                    },
                },
                "required": ["base", "source"],
            },
        },
        {
            "name": "approve_step",
            "description": "批准渐进式注入的某个步骤。接收 progressive_inject 返回的 plan_json 和 step_index。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_json": {
                        "type": "string",
                        "description": "progressive_inject 返回的完整 plan JSON 字符串",
                    },
                    "step_index": {
                        "type": "integer",
                        "description": "要批准的步骤索引（从0开始）",
                    },
                },
                "required": ["plan_json", "step_index"],
            },
        },
        {
            "name": "reject_step",
            "description": "拒绝渐进式注入的某个步骤。接收 progressive_inject 返回的 plan_json 和 step_index。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_json": {
                        "type": "string",
                        "description": "progressive_inject 返回的完整 plan JSON 字符串",
                    },
                    "step_index": {
                        "type": "integer",
                        "description": "要拒绝的步骤索引（从0开始）",
                    },
                },
                "required": ["plan_json", "step_index"],
            },
        },
    ]


async def handle_tool_call(
    server: SkillComposerServer,
    tool_name: str,
    arguments: dict[str, Any],
) -> str:
    """处理工具调用请求"""
    handlers = {
        "list_skills": lambda: server.tool_list_skills(arguments.get("query")),
        "analyze_skill": lambda: server.tool_analyze_skill(arguments["skill_name"]),
        "compare_skills": lambda: server.tool_compare_skills(
            arguments["base_skill"], arguments["candidate_skill"]
        ),
        "compose_skills": lambda: server.tool_compose_skills(
            base=arguments["base"],
            additions=arguments["additions"],
            output_mode=arguments.get("output_mode"),
            dry_run=arguments.get("dry_run", False),
            conflict_choices=arguments.get("conflict_choices"),
        ),
        "recommend_combo": lambda: server.tool_recommend_combo(
            task=arguments["task"],
            llm_provider=arguments.get("llm_provider"),
        ),
        "save_template": lambda: server.tool_save_template(
            template_name=arguments["template_name"],
            base_skill=arguments["base_skill"],
            additions=arguments["additions"],
            description=arguments.get("description", ""),
        ),
        "load_template": lambda: server.tool_load_template(arguments["template_name"]),
        "list_templates": lambda: server.tool_list_templates(),
        "configure_skills": lambda: server.tool_configure_skills(
            skill_paths=arguments["skill_paths"],
        ),
        "reload_config": lambda: server.tool_reload_config(),
        "search_patterns": lambda: server.tool_search_patterns(
            query=arguments.get("query", ""),
            category=arguments.get("category", ""),
            tags=arguments.get("tags"),
            min_success_rate=arguments.get("min_success_rate", 0.0),
            limit=arguments.get("limit", 20),
        ),
        "analyze_evolution": lambda: server.tool_analyze_evolution(
            base_skill=arguments["base_skill"],
            source_skill=arguments["source_skill"],
            include_pattern_extraction=arguments.get("include_pattern_extraction", True),
        ),
        "progressive_inject": lambda: server.tool_progressive_inject(
            base=arguments["base"],
            source=arguments["source"],
            output_mode=arguments.get("output_mode", "diff"),
            step_filter=arguments.get("step_filter"),
        ),
        "approve_step": lambda: server.tool_approve_step(
            plan_json=arguments["plan_json"],
            step_index=arguments["step_index"],
        ),
        "reject_step": lambda: server.tool_reject_step(
            plan_json=arguments["plan_json"],
            step_index=arguments["step_index"],
        ),
    }

    handler = handlers.get(tool_name)
    if handler is None:
        return json.dumps(
            {"error": f"未知工具: {tool_name}"}, ensure_ascii=False, indent=2
        )

    return await handler()


def main():
    """MCP Server 入口点 - stdio 传输"""
    logger.info("启动 Skill Composer MCP Server...")

    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import (
            CallToolRequest,
            CallToolResult,
            ListToolsResult,
            TextContent,
            Tool,
        )

        server_instance = SkillComposerServer()
        mcp_server = Server("skill-composer-mcp")

        @mcp_server.list_tools()
        async def list_tools() -> ListToolsResult:
            tools = []
            for defn in get_tool_definitions():
                tools.append(
                    Tool(
                        name=defn["name"],
                        description=defn["description"],
                        inputSchema=defn["inputSchema"],
                    )
                )
            return ListToolsResult(tools=tools)

        @mcp_server.call_tool()
        async def call_tool(
            name: str, arguments: dict[str, Any]
        ) -> CallToolResult:
            result = await handle_tool_call(server_instance, name, arguments)
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )

        async def run():
            async with stdio_server() as (read_stream, write_stream):
                await mcp_server.run(
                    read_stream, write_stream,
                    mcp_server.create_initialization_options(),
                )

        asyncio.run(run())

    except ImportError:
        # MCP SDK 未安装时，提供简化的 stdio 模式
        logger.warning("MCP SDK 未安装，运行简化模式")
        _run_simplified_mode()


def _run_simplified_mode():
    """简化模式 - 不依赖 MCP SDK，直接通过 stdin/stdout 交互"""
    server_instance = SkillComposerServer()

    logger.info("简化模式：通过 stdin/stdout 交互")
    print("Skill Composer MCP Server (简化模式)", flush=True)
    print("输入 'help' 查看可用命令", flush=True)

    while True:
        try:
            line = input("> ").strip()
            if not line:
                continue
            if line.lower() in ("help", "?"):
                print("可用命令：")
                print("  list [query]           - 列出技能")
                print("  analyze <name>         - 分析技能（六维+逆向工程）")
                print("  compare <a> <b>        - 对比技能")
                print("  compose <base> <adds>  - 组合技能")
                print("  recommend <task>       - 推荐组合")
                print("  templates              - 列出模板")
                print("  patterns [query]       - 搜索模式库")
                print("  evolve <base> <source> - 进化分析（六维对比+路线图）")
                print("  inject <base> <source> - 渐进式注入")
                print("  quit                   - 退出")
                continue
            if line.lower() == "quit":
                break

            parts = line.split()
            cmd = parts[0]

            if cmd == "list":
                query = " ".join(parts[1:]) if len(parts) > 1 else None
                result = asyncio.run(server_instance.tool_list_skills(query))
                print(result)
            elif cmd == "analyze" and len(parts) > 1:
                result = asyncio.run(server_instance.tool_analyze_skill(parts[1]))
                print(result)
            elif cmd == "compare" and len(parts) > 2:
                result = asyncio.run(
                    server_instance.tool_compare_skills(parts[1], parts[2])
                )
                print(result)
            elif cmd == "compose" and len(parts) > 2:
                base = parts[1]
                additions = parts[2:]
                result = asyncio.run(
                    server_instance.tool_compose_skills(base, additions)
                )
                print(result)
            elif cmd == "recommend" and len(parts) > 1:
                task = " ".join(parts[1:])
                result = asyncio.run(server_instance.tool_recommend_combo(task))
                print(result)
            elif cmd == "templates":
                result = asyncio.run(server_instance.tool_list_templates())
                print(result)
            else:
                print(f"未知命令: {cmd}")
        except EOFError:
            break
        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            print(f"错误: {e}")


if __name__ == "__main__":
    main()
