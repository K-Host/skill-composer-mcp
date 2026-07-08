"""
数据模型 - 使用 Pydantic 定义所有核心数据结构
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SkillModule(BaseModel):
    """能力模块"""

    name: str
    description: str = ""
    input: str | None = None
    output: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    raw_content: str = ""  # 模块原始Markdown内容


class SkillMeta(BaseModel):
    """技能元数据"""

    name: str
    description: str = ""
    version: str = "1.0.0"
    author: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    modules: list[SkillModule] = Field(default_factory=list)
    raw_content: str = ""
    path: str = ""
    hash: str = ""  # SHA256 文件哈希
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    design_patterns: list[str] = Field(default_factory=list)  # 设计模式标签


class ComparisonResult(BaseModel):
    """对比结果"""

    base_skill: str
    candidate_skill: str
    common_modules: list[str] = Field(default_factory=list)
    unique_to_base: list[str] = Field(default_factory=list)
    unique_to_candidate: list[str] = Field(default_factory=list)
    improved_in_candidate: list[dict[str, str]] = Field(default_factory=list)
    suggested_priority: str = "base"  # base / candidate
    summary: str = ""


class ConflictOption(BaseModel):
    """冲突决策选项"""

    conflict: str
    module: str = ""
    options: list[str] = Field(default_factory=list)
    default_choice: str = "A"


class DiffManifest(BaseModel):
    """差异清单"""

    added_modules: list[dict[str, str]] = Field(default_factory=list)
    removed_modules: list[dict[str, str]] = Field(default_factory=list)
    modified_modules: list[dict[str, str]] = Field(default_factory=list)
    new_dependencies: list[str] = Field(default_factory=list)
    conflict_options: list[ConflictOption] = Field(default_factory=list)


class CompositionPlan(BaseModel):
    """组合方案"""

    base_skill: str
    added_skills: list[str] = Field(default_factory=list)
    modules_to_merge: list[dict[str, Any]] = Field(default_factory=list)
    new_dependencies: list[str] = Field(default_factory=list)
    conflicts: list[ConflictOption] = Field(default_factory=list)
    diff_manifest: DiffManifest = Field(default_factory=DiffManifest)
    composed_content: str | None = None
    output_mode: str = "diff"  # diff / temp / persist
    source_hashes: dict[str, str] = Field(default_factory=dict)
    saved_path: str | None = None  # persist模式保存路径


class Template(BaseModel):
    """组合模板"""

    name: str
    base_skill: str
    additions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    description: str = ""


class DimensionScore(BaseModel):
    """六维分析单维度评分"""

    name: str
    score: float = 0.0  # 0.0 - 10.0
    description: str = ""
    evidence: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class SixDimensionReport(BaseModel):
    """六维分析报告 - Taotie 启发式框架"""

    speed: DimensionScore = Field(default_factory=lambda: DimensionScore(name="speed"))
    accuracy: DimensionScore = Field(default_factory=lambda: DimensionScore(name="accuracy"))
    robustness: DimensionScore = Field(default_factory=lambda: DimensionScore(name="robustness"))
    output_quality: DimensionScore = Field(default_factory=lambda: DimensionScore(name="output_quality"))
    prompt_strategy: DimensionScore = Field(default_factory=lambda: DimensionScore(name="prompt_strategy"))
    tool_usage: DimensionScore = Field(default_factory=lambda: DimensionScore(name="tool_usage"))
    overall_score: float = 0.0
    radar: dict[str, float] = Field(default_factory=dict)

    def compute_overall(self) -> None:
        scores = [
            self.speed.score,
            self.accuracy.score,
            self.robustness.score,
            self.output_quality.score,
            self.prompt_strategy.score,
            self.tool_usage.score,
        ]
        self.overall_score = round(sum(scores) / len(scores), 1)
        self.radar = {s.name: s.score for s in self.dimensions}

    @property
    def dimensions(self) -> list[DimensionScore]:
        return [
            self.speed,
            self.accuracy,
            self.robustness,
            self.output_quality,
            self.prompt_strategy,
            self.tool_usage,
        ]


class ReverseEngineeringReport(BaseModel):
    """逆向分析报告 - WHY 层面的分析"""

    design_rationale: list[str] = Field(default_factory=list)
    tradeoffs: list[dict[str, str]] = Field(default_factory=list)
    architectural_decisions: list[str] = Field(default_factory=list)
    hidden_assumptions: list[str] = Field(default_factory=list)
    evolution_potential: list[str] = Field(default_factory=list)


class PatternLibraryEntry(BaseModel):
    """模式库条目"""

    name: str
    category: str = ""  # prompt_design / tool_use / error_handling / …
    description: str = ""
    skills_using: list[str] = Field(default_factory=list)
    usage_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    lifecycle: str = "active"  # active / deprecated / archived
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.0
        return round(self.success_count / total * 100, 1)


class EvolutionStep(BaseModel):
    """渐进式注入的步骤"""

    dimension: str  # speed / accuracy / robustness / output_quality / prompt_strategy / tool_usage
    status: str = "pending"  # pending / sandboxing / approved / rejected / skipped
    sandbox_result: str = ""
    merged_modules: list[str] = Field(default_factory=list)
    conflicts: list[ConflictOption] = Field(default_factory=list)


class ProgressiveInjectionPlan(BaseModel):
    """渐进式注入计划"""

    base_skill: str
    source_skill: str
    steps: list[EvolutionStep] = Field(default_factory=list)
    current_step: int = 0
    status: str = "draft"  # draft / in_progress / completed / cancelled
    output_mode: str = "diff"


class SecurityViolation(Exception):
    """安全违规异常"""

    pass
