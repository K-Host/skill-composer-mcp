"""
SecurityGuard 安全沙箱测试
"""

import os
import tempfile
from pathlib import Path

import pytest

from skill_composer_mcp.core.security_guard import SecurityGuard
from skill_composer_mcp.models import SecurityViolation


@pytest.fixture
def temp_dirs():
    """创建临时目录用于测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_dir = Path(tmpdir) / "allowed"
        allowed_dir.mkdir()
        forbidden_dir = Path(tmpdir) / "forbidden"
        forbidden_dir.mkdir()
        composed_dir = Path(tmpdir) / "composed"
        composed_dir.mkdir()

        # 创建测试文件
        (allowed_dir / "test.md").write_text("test content")

        yield {
            "tmpdir": tmpdir,
            "allowed": str(allowed_dir),
            "forbidden": str(forbidden_dir),
            "composed": str(composed_dir),
        }


@pytest.fixture
def guard(temp_dirs):
    return SecurityGuard(
        allowed_roots=[temp_dirs["allowed"]],
        forbidden_dirs=[temp_dirs["forbidden"]],
        allow_read_only=True,
        composed_skills_dir=temp_dirs["composed"],
    )


class TestSecurityGuard:
    def test_resolve_path_allowed(self, guard, temp_dirs):
        """测试白名单内路径解析"""
        path = guard.resolve_path(str(Path(temp_dirs["allowed"]) / "test.md"))
        assert path.exists()

    def test_resolve_path_forbidden(self, guard, temp_dirs):
        """测试黑名单路径拒绝"""
        with pytest.raises(SecurityViolation, match="禁止目录"):
            guard.resolve_path(str(Path(temp_dirs["forbidden"]) / "something"))

    def test_resolve_path_outside_whitelist(self, guard):
        """测试白名单外路径拒绝"""
        with pytest.raises(SecurityViolation, match="不在白名单内"):
            guard.resolve_path("/tmp/arbitrary_path")

    def test_write_to_composed_dir(self, guard, temp_dirs):
        """测试写入隔离目录"""
        target = str(Path(temp_dirs["composed"]) / "new_skill.md")
        path = guard.validate_write_target(target)
        assert str(path) == str(Path(target).resolve())

    def test_write_outside_composed_dir(self, guard, temp_dirs):
        """测试写入非隔离目录被拒绝"""
        target = str(Path(temp_dirs["allowed"]) / "hack.md")
        with pytest.raises(SecurityViolation, match="不在隔离目录"):
            guard.validate_write_target(target)

    def test_compute_hash(self, guard, temp_dirs):
        """测试文件哈希计算"""
        file_path = str(Path(temp_dirs["allowed"]) / "test.md")
        h = guard.compute_hash(file_path)
        assert len(h) == 64  # SHA256 hex length
        assert h == guard.compute_hash(file_path)  # deterministic

    def test_compute_content_hash(self, guard):
        """测试内容哈希"""
        h1 = guard.compute_content_hash("hello world")
        h2 = guard.compute_content_hash("hello world")
        h3 = guard.compute_content_hash("hello world!")
        assert h1 == h2
        assert h1 != h3

    def test_is_safe_to_write_new_file(self, guard, temp_dirs):
        """测试安全写入新文件"""
        target = str(Path(temp_dirs["composed"]) / "new.md")
        assert guard.is_safe_to_write(target) is True

    def test_is_safe_to_write_existing_no_hash(self, guard, temp_dirs):
        """测试拒绝覆盖已存在文件"""
        target = str(Path(temp_dirs["composed"]) / "existing.md")
        Path(target).write_text("existing")
        assert guard.is_safe_to_write(target) is False

    def test_is_safe_to_write_existing_with_matching_hash(self, guard, temp_dirs):
        """测试哈希匹配时允许写入"""
        target = str(Path(temp_dirs["composed"]) / "match.md")
        content = "content"
        Path(target).write_text(content)
        expected_hash = guard.compute_content_hash(content)
        assert guard.is_safe_to_write(target, expected_hash) is True

    def test_is_safe_to_write_existing_with_mismatched_hash(self, guard, temp_dirs):
        """测试哈希不匹配时拒绝写入"""
        target = str(Path(temp_dirs["composed"]) / "mismatch.md")
        Path(target).write_text("old content")
        wrong_hash = guard.compute_content_hash("different content")
        assert guard.is_safe_to_write(target, wrong_hash) is False

    def test_add_allowed_root(self, guard, temp_dirs):
        """测试动态添加白名单"""
        with tempfile.TemporaryDirectory() as new_dir:
            guard.add_allowed_root(new_dir)
            path = guard.resolve_path(new_dir)
            assert str(path) == str(Path(new_dir).resolve())
