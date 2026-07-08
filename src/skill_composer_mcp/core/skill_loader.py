"""
SkillLoader - 技能加载器
扫描多个目录，支持动态发现和环境变量，建立技能索引
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from loguru import logger

from ..models import SkillMeta
from .security_guard import SecurityGuard


class SkillIndexEntry:
    """技能索引条目"""

    def __init__(self, name: str, path: str, skill_md_path: str, file_hash: str):
        self.name = name
        self.path = path  # 技能目录路径
        self.skill_md_path = skill_md_path  # SKILL.md 文件路径
        self.file_hash = file_hash

    def __repr__(self) -> str:
        return f"SkillIndexEntry(name={self.name!r}, path={self.path!r}, hash={self.file_hash[:8]}...)"


class SkillLoader:
    """技能加载器 - 扫描、索引、模糊搜索"""

    SKILL_FILE_NAMES = ["SKILL.md", "skill.md", "Skill.md"]

    def __init__(
        self,
        skill_paths: list[str],
        security_guard: SecurityGuard,
        cache_ttl: int = 60,
    ):
        self._skill_paths = [os.path.expanduser(p) for p in skill_paths]
        self._security = security_guard
        self._cache_ttl = cache_ttl
        self._cache: dict[str, SkillIndexEntry] = {}
        self._cache_time: float = 0
        self._warnings: list[str] = []

        # 动态发现：向上查找 .skills/ 或 skills/
        self._discover_project_skills()

    def _discover_project_skills(self) -> None:
        """动态上下文感知：向上查找当前工作目录的 .skills/ 或 skills/ 文件夹"""
        cwd = Path.cwd()
        for parent in [cwd, *cwd.parents]:
            for dirname in [".skills", "skills"]:
                candidate = parent / dirname
                if candidate.is_dir() and str(candidate) not in self._skill_paths:
                    self._skill_paths.append(str(candidate))
                    logger.debug(f"动态发现技能目录: {candidate}")
                    # 添加到安全白名单
                    self._security.add_allowed_root(str(candidate))
                    return  # 只取最近的一个

    def _find_skill_md(self, skill_dir: Path) -> Path | None:
        """在技能目录中查找 SKILL.md 文件"""
        for name in self.SKILL_FILE_NAMES:
            candidate = skill_dir / name
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def _scan_directory(self, root: str) -> dict[str, SkillIndexEntry]:
        """扫描单个目录，返回技能索引"""
        index: dict[str, SkillIndexEntry] = {}
        root_path = Path(root)

        if not root_path.exists() or not root_path.is_dir():
            logger.debug(f"技能目录不存在或非目录: {root}")
            return index

        try:
            # 遍历目录
            for entry in sorted(root_path.iterdir()):
                if not entry.is_dir():
                    continue

                skill_md = self._find_skill_md(entry)
                if skill_md is None:
                    continue

                skill_name = entry.name
                file_hash = SecurityGuard.compute_hash(skill_md)

                if skill_name in index:
                    self._warnings.append(
                        f"技能 '{skill_name}' 在目录 '{root}' 中重复，后者覆盖前者"
                    )

                index[skill_name] = SkillIndexEntry(
                    name=skill_name,
                    path=str(entry),
                    skill_md_path=str(skill_md),
                    file_hash=file_hash,
                )
                logger.debug(f"发现技能: {skill_name} @ {entry}")

        except PermissionError as e:
            logger.warning(f"扫描目录 '{root}' 权限不足: {e}")
        except Exception as e:
            logger.error(f"扫描目录 '{root}' 失败: {e}")

        return index

    def refresh_index(self, force: bool = False) -> dict[str, SkillIndexEntry]:
        """刷新技能索引（带缓存）"""
        now = time.time()
        if not force and self._cache and (now - self._cache_time) < self._cache_ttl:
            logger.debug("使用缓存的技能索引")
            return self._cache

        self._warnings.clear()
        index: dict[str, SkillIndexEntry] = {}

        for root in self._skill_paths:
            sub_index = self._scan_directory(root)
            for name, entry in sub_index.items():
                if name in index:
                    self._warnings.append(
                        f"技能 '{name}' 在多个目录中发现，'{entry.path}' 覆盖了 '{index[name].path}'"
                    )
                index[name] = entry

        self._cache = index
        self._cache_time = now
        logger.info(f"技能索引刷新完成，共 {len(index)} 个技能")
        if self._warnings:
            for w in self._warnings:
                logger.warning(w)

        return index

    def list_skills(self, include_description: bool = False) -> list[dict[str, str]]:
        """列出所有技能（名称+路径+哈希前8位）"""
        index = self.refresh_index()
        if not include_description:
            return [
                {
                    "name": e.name,
                    "path": e.path,
                    "hash": e.file_hash[:8] if e.file_hash else "",
                }
                for e in index.values()
            ]

        # 包含描述（需要解析 SKILL.md 的���几行）
        result: list[dict[str, str]] = []
        for entry in index.values():
            description = ""
            try:
                from .skill_parser import SkillParser

                if not hasattr(self, "_parser"):
                    self._parser = SkillParser()
                meta = self._parser.parse_file(entry.skill_md_path, entry.file_hash)
                description = meta.description
            except Exception:
                pass
            result.append(
                {
                    "name": entry.name,
                    "path": entry.path,
                    "hash": entry.file_hash[:8] if entry.file_hash else "",
                    "description": description,
                }
            )
        return result

    def resolve_skill_name(self, query: str) -> list[str]:
        """
        解析技能名称，支持部分匹配。
        返回候选技能名称列表（按匹配度排序）。
        """
        index = self.refresh_index()
        query_lower = query.lower()

        # 精确匹配
        if query in index:
            return [query]

        # 部分匹配（包含关系）
        partial_matches = [
            name for name in index if query_lower in name.lower()
        ]
        if partial_matches:
            return partial_matches

        # 反向匹配（技能名包含查询词）
        reverse_matches = [
            name for name in index if name.lower() in query_lower
        ]
        if reverse_matches:
            return reverse_matches

        return []

    def get_skill_md_path(self, skill_name: str) -> str | None:
        """获取技能的 SKILL.md 文件路径"""
        index = self.refresh_index()
        # 精确匹配
        if skill_name in index:
            return index[skill_name].skill_md_path

        # 部分匹配
        candidates = self.resolve_skill_name(skill_name)
        if candidates:
            return index[candidates[0]].skill_md_path

        return None

    def get_skill_hash(self, skill_name: str) -> str:
        """获取技能文件哈希"""
        index = self.refresh_index()
        candidates = self.resolve_skill_name(skill_name)
        if candidates:
            return index[candidates[0]].file_hash
        return ""

    def get_warnings(self) -> list[str]:
        """获取最近的警告信息"""
        return self._warnings

    @property
    def skill_paths(self) -> list[str]:
        return self._skill_paths
