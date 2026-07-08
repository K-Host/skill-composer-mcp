"""
TemplateManager 模板管理器测试
"""

import tempfile

import pytest

from skill_composer_mcp.core.template_manager import TemplateManager


@pytest.fixture
def manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield TemplateManager(templates_dir=tmpdir)


class TestTemplateManager:
    def test_save_and_load(self, manager):
        """测试保存和加载"""
        template = manager.save_template(
            name="test-template",
            base_skill="research-skill",
            additions=["writer-skill", "xiaohongshu-skill"],
            description="科研写作小红书组合",
        )
        assert template.name == "test-template"

        loaded = manager.load_template("test-template")
        assert loaded is not None
        assert loaded.base_skill == "research-skill"
        assert loaded.additions == ["writer-skill", "xiaohongshu-skill"]

    def test_load_nonexistent(self, manager):
        """测试加载不存在的模板"""
        result = manager.load_template("nonexistent")
        assert result is None

    def test_list_templates(self, manager):
        """测试列出模板"""
        manager.save_template("t1", "base1", ["add1"], "desc1")
        manager.save_template("t2", "base2", ["add2"], "desc2")

        templates = manager.list_templates()
        assert len(templates) == 2
        names = [t["name"] for t in templates]
        assert "t1" in names
        assert "t2" in names

    def test_delete_template(self, manager):
        """测试删除模板"""
        manager.save_template("to-delete", "base", ["add"])
        assert manager.delete_template("to-delete") is True
        assert manager.load_template("to-delete") is None

    def test_delete_nonexistent(self, manager):
        """测试删除不存在的模板"""
        assert manager.delete_template("nonexistent") is False

    def test_fuzzy_load(self, manager):
        """测试模糊加载"""
        manager.save_template("research-writer-combo", "base", ["add"])
        loaded = manager.load_template("research")
        assert loaded is not None
        assert loaded.name == "research-writer-combo"
