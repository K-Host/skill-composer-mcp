"""
SecurityGuard - 安全沙箱解析器
所有文件访问必经路径白名单校验，防止路径遍历攻击
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from loguru import logger

from ..models import SecurityViolation


class SecurityGuard:
    """安全守卫 - 路径白名单、哈希校验、防越权"""

    def __init__(
        self,
        allowed_roots: list[str] | None = None,
        forbidden_dirs: list[str] | None = None,
        allow_read_only: bool = True,
        composed_skills_dir: str = "./composed_skills",
    ):
        self._allowed_roots: list[Path] = []
        if allowed_roots:
            for root in allowed_roots:
                resolved = Path(os.path.expanduser(root)).resolve()
                self._allowed_roots.append(resolved)
                logger.debug(f"Allowed root: {resolved}")

        self._forbidden_dirs: list[Path] = []
        if forbidden_dirs:
            for d in forbidden_dirs:
                resolved = Path(os.path.expanduser(d)).resolve()
                self._forbidden_dirs.append(resolved)

        self._allow_read_only = allow_read_only
        self._composed_skills_dir = Path(os.path.expanduser(composed_skills_dir)).resolve()
        # 组合目录也加入白名单
        if self._composed_skills_dir not in self._allowed_roots:
            self._allowed_roots.append(self._composed_skills_dir)

    def add_allowed_root(self, root: str) -> None:
        """动态添加白名单路径"""
        resolved = Path(os.path.expanduser(root)).resolve()
        if resolved not in self._allowed_roots:
            self._allowed_roots.append(resolved)
            logger.debug(f"Added allowed root: {resolved}")

    def resolve_path(self, requested_path: str, for_write: bool = False) -> Path:
        """
        解析并校验路径安全性。
        1. 解析为绝对路径（处理符号链接）
        2. 检查白名单
        3. 检查黑名单
        4. 若 for_write=True，额外校验写入目标在隔离目录内

        Raises:
            SecurityViolation: 路径不安全时抛出
        """
        # 展开用户目录
        expanded = os.path.expanduser(requested_path)
        # 解析为绝对路径，follow symlinks
        abs_path = Path(expanded).resolve()

        # 检查黑名单
        for forbidden in self._forbidden_dirs:
            try:
                abs_path.relative_to(forbidden)
                raise SecurityViolation(
                    f"路径 '{requested_path}' 位于禁止目录 '{forbidden}' 内"
                )
            except ValueError:
                # 不在禁止目录内，继续
                pass

        # 检查白名单
        in_whitelist = False
        for root in self._allowed_roots:
            try:
                abs_path.relative_to(root)
                in_whitelist = True
                break
            except ValueError:
                continue

        if not in_whitelist:
            raise SecurityViolation(
                f"路径 '{requested_path}'（解析为 '{abs_path}'）不在白名单内。"
                f"允许的根目录: {[str(r) for r in self._allowed_roots]}"
            )

        # 写入操作额外校验
        if for_write:
            if self._allow_read_only:
                # 只读模式下，写入仅允许到组合目录
                try:
                    abs_path.relative_to(self._composed_skills_dir)
                except ValueError:
                    raise SecurityViolation(
                        f"写入路径 '{requested_path}' 不在隔离目录 "
                        f"'{self._composed_skills_dir}' 内。只读模式禁止写入其他位置。"
                    )

        logger.debug(f"路径校验通过: {requested_path} -> {abs_path}")
        return abs_path

    def validate_write_target(self, target_path: str) -> Path:
        """校验写入目标路径，确保在隔离目录内"""
        return self.resolve_path(target_path, for_write=True)

    def check_path_traversal(self, path: str) -> bool:
        """
        检查路径是否在白名单内（即非遍历攻击）。
        白名单与符号链接解析已由 resolve_path 完成，此处仅作布尔封装。
        """
        try:
            self.resolve_path(path)
            return True
        except SecurityViolation:
            return False

    @staticmethod
    def compute_hash(file_path: str | Path) -> str:
        """计算文件 SHA256 哈希"""
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return ""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """计算字符串内容 SHA256 哈希"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def is_safe_to_write(self, target_path: str, expected_hash: str | None = None) -> bool:
        """
        检查是否安全写入：
        - 目标在隔离目录内
        - 若目标已存在，校验哈希是否一致（防止误覆盖）
        """
        try:
            resolved = self.validate_write_target(target_path)
        except SecurityViolation:
            return False

        if resolved.exists():
            if expected_hash is not None:
                existing_hash = self.compute_hash(resolved)
                if existing_hash != expected_hash:
                    logger.warning(
                        f"目标文件已存在且内容不同，拒绝覆盖: {resolved} "
                        f"(existing={existing_hash[:8]}, expected={expected_hash[:8]})"
                    )
                    return False
            else:
                # 目标存在但没有提供期望哈希，拒绝写入
                logger.warning(f"目标文件已存在，拒绝覆盖: {resolved}")
                return False

        return True
