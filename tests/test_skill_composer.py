"""
SkillComposer 技能组合引擎测试
"""

import tempfile
from pathlib import Path

import pytest

from skill_composer_mcp.core.security_guard import SecurityGuard
from skill_composer_mcp.core.skill_analyzer import SkillAnalyzer
from skill_composer_mcp.core.skill_composer import SkillComposer
from skill_composer_mcp.core.skill_loader import SkillLoader
from skill_composer_mcp.core.skill_parser import SkillParser


@pytest.fixture
def setup_env():
    """创建完整的测试环境"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        skills_dir.mkdir()
        composed_dir = Path(tmpdir) / "composed"
        composed_dir.mkdir()

        # 创建技能A（基础）
        skill_a = skills_dir / "skill-a"
        skill_a.mkdir()
        (skill_a / "SKILL.md").write_text(
            "---\nname: skill-a\ndescription: Base skill\nversion: 1.0.0\n---\n"
            "# skill-a\n\n## 能力：搜索\n\nSearch with requests.\n\n"
            "## 模块：缓存\n\nCache with redis.\n"
        )

        # 创建技能B（候选）
        skill_b = skills_dir / "skill-b"
        skill_b.mkdir()
        (skill_b / "SKILL.md").write_text(
            "---\nname: skill-b\ndescription: Candidate skill\nversion: 1.0.0\n---\n"
            "# skill-b\n\n## 能力：搜索\n\nEnhanced search with httpx and better logic. "
            "More detailed implementation here.\n\n## 模块：导出\n\nExport to CSV.\n\n"
            "## 能力：分析\n\nData analysis with pandas.\n"
        )

        guard = SecurityGuard(
            allowed_roots=[str(skills_dir)],
            composed_skills_dir=str(composed_dir),
        )
        loader = SkillLoader(
            skill_paths=[str(skills_dir)],
            security_guard=guard,
            cache_ttl=0,
        )
        parser = SkillParser()
        analyzer = SkillAnalyzer()
        composer = SkillComposer(
            loader=loader,
            parser=parser,
            analyzer=analyzer,
            security=guard,
            composed_skills_dir=str(composed_dir),
        )

        yield {
            "composer": composer,
            "skills_dir": str(skills_dir),
            "composed_dir": str(composed_dir),
        }


class TestSkillComposer:
    def test_compose_diff_mode(self, setup_env):
        """测试 diff 模式"""
        composer = setup_env["composer"]
        plan = composer.compose(
            base="skill-a",
            additions=["skill-b"],
            output_mode="diff",
        )
        assert plan.base_skill == "skill-a"
        assert "skill-b" in plan.added_skills
        assert plan.composed_content is None
        assert plan.output_mode == "diff"
        # 应该有差异清单
        assert len(plan.diff_manifest.added_modules) > 0  # 导出、分析模块
        assert len(plan.diff_manifest.modified_modules) > 0  # 搜索模块被改进

    def test_compose_dry_run(self, setup_env):
        """测试 dry-run 模式"""
        composer = setup_env["composer"]
        plan = composer.compose(
            base="skill-a",
            additions=["skill-b"],
            dry_run=True,
        )
        assert plan.output_mode == "dry-run"
        assert plan.composed_content is None
        # dry-run 也应有差异清单
        assert len(plan.diff_manifest.added_modules) > 0

    def test_compose_temp_mode(self, setup_env):
        """测试 temp 模式"""
        composer = setup_env["composer"]
        plan = composer.compose(
            base="skill-a",
            additions=["skill-b"],
            output_mode="temp",
        )
        assert plan.output_mode == "temp"
        assert plan.composed_content is not None
        assert "skill-a" in plan.composed_content
        assert "skill-b" in plan.composed_content
        assert plan.saved_path is None  # temp 不保存

    def test_compose_persist_mode(self, setup_env):
        """测试 persist 模式"""
        composer = setup_env["composer"]
        plan = composer.compose(
            base="skill-a",
            additions=["skill-b"],
            output_mode="persist",
        )
        assert plan.output_mode == "persist"
        assert plan.composed_content is not None
        assert plan.saved_path is not None
        # 文件应该存在
        saved_path = Path(plan.saved_path)
        assert saved_path.exists()
        assert (saved_path / "SKILL.md").exists()
        assert (saved_path / "composition_meta.json").exists()

    def test_compose_source_hashes(self, setup_env):
        """测试源哈希记录"""
        composer = setup_env["composer"]
        plan = composer.compose(
            base="skill-a",
            additions=["skill-b"],
            output_mode="diff",
        )
        assert "skill-a" in plan.source_hashes
        assert "skill-b" in plan.source_hashes
        assert len(plan.source_hashes["skill-a"]) == 64

    def test_compose_nonexistent_skill(self, setup_env):
        """测试组合不存在的技能"""
        composer = setup_env["composer"]
        with pytest.raises(FileNotFoundError):
            composer.compose(
                base="nonexistent",
                additions=["skill-b"],
                output_mode="diff",
            )

    def test_compose_multiple_additions(self, setup_env):
        """测试多个融合技能"""
        composer = setup_env["composer"]
        # skill-b 已存在，添加自己看是否正常
        plan = composer.compose(
            base="skill-a",
            additions=["skill-b"],
            output_mode="diff",
        )
        assert len(plan.added_skills) == 1

    def test_diff_manifest_structure(self, setup_env):
        """测试差异清单结构"""
        composer = setup_env["composer"]
        plan = composer.compose(
            base="skill-a",
            additions=["skill-b"],
            output_mode="diff",
        )
        manifest = plan.diff_manifest
        # added_modules 应该包含"导出"和"分析"
        added_names = [m["module"] for m in manifest.added_modules]
        assert any("导出" in n for n in added_names)
        assert any("分析" in n for n in added_names)
        # modified_modules 应该包含"搜索"
        modified_names = [m["module"] for m in manifest.modified_modules]
        assert any("搜索" in n for n in modified_names)
