"""
SkillLoader 技能加载器测试
"""

import tempfile
from pathlib import Path

import pytest

from skill_composer_mcp.core.security_guard import SecurityGuard
from skill_composer_mcp.core.skill_loader import SkillLoader


@pytest.fixture
def temp_skills():
    """创建临时技能目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        skills_dir.mkdir()

        # 创建技能A
        skill_a = skills_dir / "skill-a"
        skill_a.mkdir()
        (skill_a / "SKILL.md").write_text("# Skill A\n\nTest skill A")

        # 创建技能B
        skill_b = skills_dir / "skill-b"
        skill_b.mkdir()
        (skill_b / "SKILL.md").write_text("---\nname: skill-b\n---\n# Skill B")

        # 创建非技能目录（无 SKILL.md）
        not_skill = skills_dir / "not-a-skill"
        not_skill.mkdir()
        (not_skill / "readme.md").write_text("not a skill")

        yield str(skills_dir)


@pytest.fixture
def loader(temp_skills):
    guard = SecurityGuard(
        allowed_roots=[temp_skills],
        composed_skills_dir=str(Path(temp_skills) / "../composed"),
    )
    return SkillLoader(
        skill_paths=[temp_skills],
        security_guard=guard,
        cache_ttl=0,  # 测试时不缓存
    )


class TestSkillLoader:
    def test_list_skills(self, loader):
        """测试列出技能"""
        skills = loader.list_skills()
        names = [s["name"] for s in skills]
        assert "skill-a" in names
        assert "skill-b" in names
        assert "not-a-skill" not in names

    def test_resolve_exact_name(self, loader):
        """测试精确匹配"""
        candidates = loader.resolve_skill_name("skill-a")
        assert candidates == ["skill-a"]

    def test_resolve_partial_name(self, loader):
        """测试部分匹配"""
        candidates = loader.resolve_skill_name("skill")
        assert len(candidates) == 2

    def test_resolve_no_match(self, loader):
        """测试无匹配"""
        candidates = loader.resolve_skill_name("nonexistent")
        assert candidates == []

    def test_get_skill_md_path(self, loader):
        """测试获取 SKILL.md 路径"""
        path = loader.get_skill_md_path("skill-a")
        assert path is not None
        assert path.endswith("SKILL.md")

    def test_get_skill_hash(self, loader):
        """测试获取文件哈希"""
        h = loader.get_skill_hash("skill-a")
        assert len(h) == 64  # SHA256

    def test_refresh_index_force(self, loader):
        """测试强制刷新索引"""
        index1 = loader.refresh_index(force=True)
        assert len(index1) == 2
