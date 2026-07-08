"""
SkillAnalyzer 技能分析器测试
"""

import pytest

from skill_composer_mcp.core.skill_analyzer import SkillAnalyzer
from skill_composer_mcp.core.skill_parser import SkillParser
from skill_composer_mcp.models import SkillMeta, SkillModule


@pytest.fixture
def analyzer():
    return SkillAnalyzer()


@pytest.fixture
def parser():
    return SkillParser()


def make_skill(
    name: str,
    modules: list[str],
    tech_stack: list[str] | None = None,
    design_patterns: list[str] | None = None,
) -> SkillMeta:
    """创建测试技能"""
    return SkillMeta(
        name=name,
        description=f"Skill {name}",
        modules=[
            SkillModule(name=m, description=f"Module {m}", raw_content=f"## {m}\nContent for {m}")
            for m in modules
        ],
        tech_stack=tech_stack or [],
        design_patterns=design_patterns or [],
    )


class TestSkillAnalyzer:
    def test_analyze(self, analyzer):
        """测试技能分析"""
        skill = make_skill("test", ["search", "cache"], ["python", "redis"])
        report = analyzer.analyze(skill)
        assert report["name"] == "test"
        assert report["module_count"] == 2
        assert "python" in report["tech_stack"]

    def test_compare_common_modules(self, analyzer):
        """测试共同模块检测"""
        base = make_skill("base", ["search", "cache", "export"])
        candidate = make_skill("cand", ["search", "cache", "analyze"])
        result = analyzer.compare(base, candidate)
        assert "search" in result.common_modules
        assert "cache" in result.common_modules
        assert "export" in result.unique_to_base
        assert "analyze" in result.unique_to_candidate

    def test_compare_suggested_priority(self, analyzer):
        """测试建议优先级"""
        base = make_skill("base", ["mod1"])
        candidate = make_skill("cand", ["mod1", "mod2", "mod3", "mod4"])
        result = analyzer.compare(base, candidate)
        # 候选有更多独有模块，应建议 candidate
        assert result.suggested_priority == "candidate"

    def test_compare_tech_stack_diff(self, analyzer):
        """测试技术栈差异"""
        base = make_skill("base", ["mod1"], tech_stack=["python", "redis"])
        candidate = make_skill("cand", ["mod1", "mod2"], tech_stack=["python", "playwright"])
        result = analyzer.compare(base, candidate)
        # 应检测到 playwright 是候选独有的
        improved_tech = [i for i in result.improved_in_candidate if i["module"] == "tech_stack"]
        assert len(improved_tech) > 0

    def test_compare_summary(self, analyzer):
        """测试总结生成"""
        base = make_skill("base", ["a", "b"])
        candidate = make_skill("cand", ["a", "c"])
        result = analyzer.compare(base, candidate)
        assert "base" in result.summary
        assert "cand" in result.summary
