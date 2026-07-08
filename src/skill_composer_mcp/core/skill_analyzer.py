"""
SkillAnalyzer - 技能分析器
深度分析技能，六维评估框架 + 逆向工程 + 设计模式提取
"""

from __future__ import annotations

import re

from loguru import logger

from ..models import (
    ComparisonResult,
    DimensionScore,
    ReverseEngineeringReport,
    SixDimensionReport,
    SkillMeta,
)


class SkillAnalyzer:
    """技能分析器"""

    # 六维关键词映射
    _DIMENSION_KEYWORDS: dict[str, dict[str, list[str]]] = {
        "speed": {
            "positive": [
                "快速", "高效", "性能", "缓存", "并发", "并行", "异步",
                "timeout", "超时", "响应", "延迟", "吞吐", "优化",
                "fast", "quick", "cache", "concurrent", "parallel", "async",
            ],
            "evidence": [
                "非阻塞", "流式", "分批", "限流", "节流",
                "non-blocking", "streaming", "batch", "throttle", "rate limit",
            ],
        },
        "accuracy": {
            "positive": [
                "校验", "验证", "断言", "匹配", "精确", "严格",
                "validate", "verify", "assert", "exact", "strict",
                "正则", "regex", "schema", "模式匹配",
            ],
            "evidence": [
                "类型检查", "边界测试", "模糊匹配", "容忍度",
                "type check", "boundary", "fuzzy match", "tolerance",
            ],
        },
        "robustness": {
            "positive": [
                "错误处理", "异常", "重试", "降级", "熔断", "回退",
                "error", "exception", "retry", "fallback", "circuit breaker",
                "容错", "恢复", "recover", "resilience",
            ],
            "evidence": [
                "超时重试", "幂等", "事务", "补偿",
                "idempotent", "transaction", "compensation", "saga",
            ],
        },
        "output_quality": {
            "positive": [
                "JSON", "YAML", "Markdown", "格式化", "排版",
                "整洁", "清晰", "可读", "readable", "pretty",
                "结构化", "structured", "表格", "table",
            ],
            "evidence": [
                "分页", "排序", "过滤", "高亮", "着色",
                "paginate", "sort", "filter", "highlight", "colorize",
            ],
        },
        "prompt_strategy": {
            "positive": [
                "提示词", "prompt", "system prompt", "instruction",
                "上下文", "context", "few-shot", "chain-of-thought",
                "模板", "template", "角色", "role",
            ],
            "evidence": [
                "分步提示", "思维链", "示例", "约束", "格式控制",
                "step by step", "CO T", "example", "constraint", "format control",
            ],
        },
        "tool_usage": {
            "positive": [
                "工具调用", "tool", "function calling", "MCP", "API",
                "CLI", "命令", "command", "shell", "exec",
                "HTTP", "请求", "request", "curl", "wget",
            ],
            "evidence": [
                "工具链", "管道", "pipe", "组合", "编排",
                "tool chain", "pipeline", "orchestrate", "workflow",
            ],
        },
    }

    def analyze(
        self, skill: SkillMeta, extract_patterns: bool = True
    ) -> dict:
        """
        深度分析指定技能。
        返回六维评估 + 模块/技术栈/设计模式 + 逆向工程（WHY分析）。
        """
        six_dim = self._six_dimension_analysis(skill)
        reverse = self._reverse_engineer(skill)
        patterns = self._extract_patterns(skill) if extract_patterns else []

        return {
            "name": skill.name,
            "description": skill.description,
            "version": skill.version,
            "author": skill.author,
            "tech_stack": skill.tech_stack,
            "modules": [
                {
                    "name": m.name,
                    "description": m.description,
                    "dependencies": m.dependencies,
                }
                for m in skill.modules
            ],
            "design_patterns": patterns + skill.design_patterns,
            "module_count": len(skill.modules),
            "hash": skill.hash[:8] if skill.hash else "",
            "six_dimension": six_dim.model_dump(),
            "reverse_engineering": reverse.model_dump(),
        }

    def _six_dimension_analysis(self, skill: SkillMeta) -> SixDimensionReport:
        """六维分析：速度、准确度、鲁棒性、输出质量、提示策略、工具使用"""
        combined_text = (
            skill.description
            + " "
            + " ".join(m.raw_content for m in skill.modules)
            + " "
            + " ".join(skill.tech_stack)
            + " "
            + " ".join(skill.design_patterns)
        ).lower()

        report = SixDimensionReport()

        for dim_name in ("speed", "accuracy", "robustness", "output_quality", "prompt_strategy", "tool_usage"):
            keywords = self._DIMENSION_KEYWORDS.get(dim_name, {})
            positive = keywords.get("positive", [])
            evidence_words = keywords.get("evidence", [])

            score = 3.0  # 基础分
            evidence_found: list[str] = []
            suggestions: list[str] = []

            # 正面关键词命中
            hits = sum(1 for kw in positive if kw.lower() in combined_text)
            score += min(hits * 0.5, 4.0)

            # 高级证据命中
            ev_hits = [ew for ew in evidence_words if ew.lower() in combined_text]
            for ev in ev_hits:
                evidence_found.append(f"检测到高级特征: {ev}")
                score += 0.8

            # 技术栈增强
            for ts in skill.tech_stack:
                ts_lower = ts.lower()
                if dim_name == "speed" and any(
                    x in ts_lower for x in ("redis", "memcache", "async", "thread")
                ):
                    evidence_found.append(f"技术栈支持速度: {ts}")
                    score += 0.5
                elif dim_name == "robustness" and any(
                    x in ts_lower for x in ("retry", "polly", "resilience", "circuit")
                ):
                    evidence_found.append(f"技术栈支持鲁棒性: {ts}")
                    score += 0.5

            # 反转优化：如果某些维度完全没有命中，给出建议
            if hits == 0 and not ev_hits:
                suggestions.append(f"缺乏 {dim_name} 相关关键词，考虑补充")

            # 模块级细粒度分析
            for mod in skill.modules:
                mod_lower = mod.raw_content.lower() if mod.raw_content else ""
                if dim_name == "prompt_strategy" and (
                    "你是一个" in mod_lower or "you are" in mod_lower or "# 提示词" in mod_lower
                ):
                    evidence_found.append(f"模块 '{mod.name}' 包含提示词定义")
                    score += 0.5

            score = min(max(score, 0.0), 10.0)

            dim_score = DimensionScore(
                name=dim_name,
                score=round(score, 1),
                description=f"{dim_name} 维度评分",
                evidence=evidence_found,
                suggestions=suggestions,
            )
            setattr(report, dim_name, dim_score)

        report.compute_overall()
        return report

    def _reverse_engineer(self, skill: SkillMeta) -> ReverseEngineeringReport:
        """逆向工程：分析设计理念、权衡、架构决策"""
        combined = (
            skill.description
            + " "
            + " ".join(m.raw_content for m in skill.modules)
        )

        rationale: list[str] = []
        tradeoffs: list[dict[str, str]] = []
        decisions: list[str] = []
        assumptions: list[str] = []
        potential: list[str] = []

        # 设计理念
        if "依赖" in combined or "dependency" in combined.lower():
            rationale.append("显式声明依赖关系，确保可复现性")
        if "安全" in combined or "security" in combined.lower():
            rationale.append("内置安全检查机制，防止越权访问")
        if "多平台" in combined or "cross-platform" in combined.lower():
            rationale.append("跨平台兼容性设计")
        if "回退" in combined or "fallback" in combined.lower():
            rationale.append("降级策略优先于失败")

        # 技术栈推断设计决策
        ts = set(skill.tech_stack)
        if ts & {"python", "powershell", "bash", "node"}:
            decisions.append("选择脚本语言实现，强调快速迭代和灵活性")
        if ts & {"docker", "container"}:
            decisions.append("容器化部署，环境一致性")
        if ts & {"sqlite", "postgresql", "mysql", "redis"}:
            decisions.append("有状态设计，数据持久化")

        # 模块数量推断复杂度
        if len(skill.modules) > 5:
            decisions.append(f"{len(skill.modules)} 个模块，中等复杂度，需要清晰的模块边界")
        if len(skill.modules) > 10:
            decisions.append("{len(skill.modules)} 个模块，高复杂度，建议考虑子技能拆分")

        # 权衡分析
        if any("detail" in m.description.lower() or "详细" in m.description for m in skill.modules):
            tradeoffs.append({
                "aspect": "详细度 vs 性能",
                "tradeoff": "内容详细但可能增加推理延迟",
            })
        if ts & {"regex", "正则"}:
            tradeoffs.append({
                "aspect": "通用性 vs 精确性",
                "tradeoff": "正则提供了灵活性但可能误匹配边缘情况",
            })
        if any("缓存" in m.raw_content or "cache" in m.raw_content.lower() for m in skill.modules):
            tradeoffs.append({
                "aspect": "新鲜度 vs 速度",
                "tradeoff": "缓存提高了响应速度但可能返回过时数据",
            })

        # 隐藏假设
        if "~" in combined or "$HOME" in combined or "%USERPROFILE%" in combined:
            assumptions.append("假设特定的主目录结构")
        if "linux" in combined.lower() or "unix" in combined.lower():
            assumptions.append("假设类 Unix 环境")
        if "api_key" in combined.lower() or "api key" in combined.lower() or "令牌" in combined:
            assumptions.append("假设外部 API 密钥可用")

        # 进化潜力
        if ts & {"ollama", "llm", "openai"}:
            potential.append("可以扩展支持更多 LLM 提供商")
        if any("测试" in m.name or "test" in m.name.lower() for m in skill.modules):
            potential.append("已有测试模块，可以增加覆盖率和自动化测试")
        if not ts & {"docker", "container"}:
            potential.append("可以考虑容器化以简化部署")

        if not rationale:
            rationale.append("设计理念隐式，建议在前言中明确设计目标")

        return ReverseEngineeringReport(
            design_rationale=rationale,
            tradeoffs=tradeoffs,
            architectural_decisions=decisions,
            hidden_assumptions=assumptions,
            evolution_potential=potential,
        )

    def _extract_patterns(self, skill: SkillMeta) -> list[str]:
        """从技能中提取设计模式（基于规则）"""
        patterns: list[str] = []
        combined = " ".join(m.raw_content for m in skill.modules).lower()

        pattern_rules = [
            ("重试策略", ["重试", "retry", "再次尝试"]),
            ("缓存策略", ["缓存", "cache", "缓存穿透", "缓存雪崩"]),
            ("并发控制", ["并发", "concurrent", "锁", "lock", "互斥", "mutex"]),
            ("异步处理", ["异步", "async", "await", "非阻塞", "non-blocking"]),
            ("管道模式", ["管道", "pipe", "pipeline", "链式", "chain"]),
            ("策略模式", ["策略", "strategy", "可切换", "plugable"]),
            ("观察者模式", ["事件", "event", "订阅", "subscribe", "publish"]),
            ("工厂模式", ["工厂", "factory", "创建器", "builder"]),
            ("单例模式", ["单例", "singleton", "全局唯一"]),
            ("适配器模式", ["适配", "adapter", "包装", "wrapper"]),
            ("降级策略", ["降级", "fallback", "熔断", "circuit breaker"]),
            ("批处理", ["批处理", "batch", "批量", "chunk"]),
            ("流式处理", ["流式", "stream", "chunked", "增量"]),
            ("模板方法", ["模板方法", "skeleton", "骨架"]),
            ("沙箱模式", ["沙箱", "sandbox", "隔离", "isolation"]),
        ]

        for pattern_name, keywords in pattern_rules:
            if any(kw in combined for kw in keywords):
                patterns.append(pattern_name)

        return patterns

    def compare(
        self,
        base: SkillMeta,
        candidate: SkillMeta,
    ) -> ComparisonResult:
        """
        对比两个技能的差异。
        输出：共同能力、独有能力、改进点、建议优先级。
        """
        base_module_names = {m.name for m in base.modules}
        candidate_module_names = {m.name for m in candidate.modules}

        common = list(base_module_names & candidate_module_names)
        unique_to_base = list(base_module_names - candidate_module_names)
        unique_to_candidate = list(candidate_module_names - base_module_names)

        # 分析候选技能做得更好的模块
        improved: list[dict[str, str]] = []
        base_modules_map = {m.name: m for m in base.modules}
        candidate_modules_map = {m.name: m for m in candidate.modules}

        for name in common:
            base_mod = base_modules_map.get(name)
            cand_mod = candidate_modules_map.get(name)
            if base_mod and cand_mod:
                base_len = len(base_mod.raw_content)
                cand_len = len(cand_mod.raw_content)
                if cand_len > base_len * 1.2:
                    improved.append(
                        {
                            "module": name,
                            "reason": f"候选技能的该模块内容更丰富 ({cand_len} vs {base_len} 字符)",
                            "candidate_value": str(cand_len),
                            "base_value": str(base_len),
                        }
                    )

                if len(cand_mod.dependencies) > len(base_mod.dependencies):
                    improved.append(
                        {
                            "module": name,
                            "reason": f"候选技能依赖更完整 ({len(cand_mod.dependencies)} vs {len(base_mod.dependencies)})",
                            "candidate_value": str(len(cand_mod.dependencies)),
                            "base_value": str(len(base_mod.dependencies)),
                        }
                    )

        # 设计模式对比
        base_patterns = set(base.design_patterns)
        candidate_patterns = set(candidate.design_patterns)
        patterns_only_in_candidate = candidate_patterns - base_patterns
        if patterns_only_in_candidate:
            improved.append(
                {
                    "module": "design_patterns",
                    "reason": f"候选技能有额外设计模式: {', '.join(patterns_only_in_candidate)}",
                    "candidate_value": ", ".join(candidate_patterns),
                    "base_value": ", ".join(base_patterns),
                }
            )

        # 六维对比
        base_six = self._six_dimension_analysis(base)
        cand_six = self._six_dimension_analysis(candidate)
        if cand_six.overall_score > base_six.overall_score + 0.5:
            improved.append(
                {
                    "module": "six_dimension",
                    "reason": (
                        f"候选技能六维评分更高 ({cand_six.overall_score} vs {base_six.overall_score})"
                    ),
                    "candidate_value": str(cand_six.overall_score),
                    "base_value": str(base_six.overall_score),
                    "radar_candidate": cand_six.radar,
                    "radar_base": base_six.radar,
                }
            )

        # 技术栈对比
        base_stack = set(base.tech_stack)
        candidate_stack = set(candidate.tech_stack)
        stack_only_in_candidate = candidate_stack - base_stack
        if stack_only_in_candidate:
            improved.append(
                {
                    "module": "tech_stack",
                    "reason": f"候选技能有额外技术栈: {', '.join(stack_only_in_candidate)}",
                    "candidate_value": ", ".join(candidate_stack),
                    "base_value": ", ".join(base_stack),
                }
            )

        suggested_priority = "base"
        if len(unique_to_candidate) > len(unique_to_base) or len(improved) >= 2:
            suggested_priority = "candidate"

        summary_parts: list[str] = []
        summary_parts.append(f"基础技能 '{base.name}' 有 {len(base.modules)} 个模块")
        summary_parts.append(f"候选技能 '{candidate.name}' 有 {len(candidate.modules)} 个模块")
        summary_parts.append(f"共同模块 {len(common)} 个")
        summary_parts.append(f"候选独有 {len(unique_to_candidate)} 个")
        if improved:
            summary_parts.append(f"候选改进点 {len(improved)} 个")
        summary_parts.append(f"建议优先级: {suggested_priority}")

        return ComparisonResult(
            base_skill=base.name,
            candidate_skill=candidate.name,
            common_modules=common,
            unique_to_base=unique_to_base,
            unique_to_candidate=unique_to_candidate,
            improved_in_candidate=improved,
            suggested_priority=suggested_priority,
            summary="；".join(summary_parts),
        )

    def get_module_by_name(
        self, skill: SkillMeta, module_name: str
    ) -> SkillMeta.modules.__class__ | None:
        """根据名称获取技能模块"""
        for m in skill.modules:
            if m.name == module_name:
                return m
        return None
