"""
PatternLibrary - 持久化模式库
存储从技能中提取的可复用模式，支持成功追踪和生命周期管理。
数据保存在 ~/.composed_skills/pattern-library.json
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from threading import Lock

from loguru import logger

from ..models import PatternLibraryEntry


class PatternLibrary:
    """持久化模式库"""

    def __init__(
        self,
        storage_path: str = "~/.composed_skills/pattern-library.json",
    ):
        self._path = Path(os.path.expanduser(storage_path))
        self._lock = Lock()
        self._entries: dict[str, PatternLibraryEntry] = {}
        self._load()

    def _load(self) -> None:
        """从磁盘加载模式库"""
        if not self._path.exists():
            logger.info(f"模式库文件不存在，将创建: {self._path}")
            self._entries = {}
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for item in data.get("entries", []):
                # 恢复 datetime 字段
                for dt_field in ("created_at", "updated_at"):
                    if isinstance(item.get(dt_field), str):
                        item[dt_field] = datetime.fromisoformat(item[dt_field])
                entry = PatternLibraryEntry(**item)
                self._entries[entry.name] = entry
            logger.info(f"模式库已加载: {len(self._entries)} 条模式")
        except Exception as e:
            logger.error(f"加载模式库失败: {e}")
            self._entries = {}

    def _save(self) -> None:
        """保存到磁盘"""
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            entries_data = []
            for e in self._entries.values():
                d = e.model_dump()
                d["created_at"] = d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else d["created_at"]
                d["updated_at"] = d["updated_at"].isoformat() if hasattr(d["updated_at"], "isoformat") else d["updated_at"]
                entries_data.append(d)
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "count": len(self._entries),
                "entries": entries_data,
            }
            self._path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

    def add_or_update(
        self,
        name: str,
        category: str = "",
        description: str = "",
        skill_name: str = "",
        tags: list[str] | None = None,
    ) -> PatternLibraryEntry:
        """添加或更新模式条目"""
        with self._lock:
            if name in self._entries:
                entry = self._entries[name]
                entry.usage_count += 1
                if skill_name and skill_name not in entry.skills_using:
                    entry.skills_using.append(skill_name)
                if description:
                    entry.description = description
                if category:
                    entry.category = category
                if tags:
                    for t in tags:
                        if t not in entry.tags:
                            entry.tags.append(t)
                entry.updated_at = datetime.now()
            else:
                entry = PatternLibraryEntry(
                    name=name,
                    category=category,
                    description=description,
                    skills_using=[skill_name] if skill_name else [],
                    usage_count=1,
                    tags=tags or [],
                )
                self._entries[name] = entry

        self._save()
        return entry

    def record_success(self, name: str) -> None:
        """记录模式使用成功"""
        with self._lock:
            entry = self._entries.get(name)
            if entry:
                entry.success_count += 1
                entry.updated_at = datetime.now()
        self._save()

    def record_fail(self, name: str) -> None:
        """记录模式使用失败"""
        with self._lock:
            entry = self._entries.get(name)
            if entry:
                entry.fail_count += 1
                entry.updated_at = datetime.now()
        self._save()

    def search(
        self,
        query: str = "",
        category: str = "",
        tags: list[str] | None = None,
        lifecycle: str = "active",
        min_success_rate: float = 0.0,
        limit: int = 20,
    ) -> list[dict]:
        """搜索模式库"""
        results: list[PatternLibraryEntry] = []
        query_lower = query.lower()

        for entry in self._entries.values():
            if entry.lifecycle != lifecycle:
                continue
            if entry.success_rate < min_success_rate:
                continue
            if category and entry.category != category:
                continue
            if tags:
                if not any(t in entry.tags for t in tags):
                    continue

            if query:
                if (
                    query_lower in entry.name.lower()
                    or query_lower in entry.description.lower()
                ):
                    results.append(entry)
            else:
                results.append(entry)

        results.sort(key=lambda e: e.usage_count, reverse=True)

        return [
            {
                "name": e.name,
                "category": e.category,
                "description": e.description[:100] if e.description else "",
                "skills_using": e.skills_using,
                "usage_count": e.usage_count,
                "success_rate": e.success_rate,
                "lifecycle": e.lifecycle,
                "tags": e.tags,
            }
            for e in results[:limit]
        ]

    def get_categories(self) -> list[str]:
        """获取所有模式分类"""
        cats: set[str] = set()
        for e in self._entries.values():
            if e.category:
                cats.add(e.category)
        return sorted(cats)

    def get_statistics(self) -> dict:
        """获取模式库统计"""
        active = sum(1 for e in self._entries.values() if e.lifecycle == "active")
        deprecated = sum(1 for e in self._entries.values() if e.lifecycle == "deprecated")
        archived = sum(1 for e in self._entries.values() if e.lifecycle == "archived")
        total_uses = sum(e.usage_count for e in self._entries.values())
        avg_success = (
            sum(e.success_rate for e in self._entries.values()) / len(self._entries)
            if self._entries
            else 0.0
        )

        return {
            "total_patterns": len(self._entries),
            "active": active,
            "deprecated": deprecated,
            "archived": archived,
            "total_uses": total_uses,
            "avg_success_rate": round(avg_success, 1),
            "categories": self.get_categories(),
            "storage_path": str(self._path),
        }

    def auto_extract_from_skill(
        self, skill_name: str, description: str, tech_stack: list[str], modules: list
    ) -> list[PatternLibraryEntry]:
        """从技能描述自动提取模式并入库"""
        combined = description.lower() + " " + " ".join(ts.lower() for ts in tech_stack)
        for mod in modules:
            combined += " " + (mod.raw_content if hasattr(mod, "raw_content") else mod.get("raw_content", ""))

        extracted: list[PatternLibraryEntry] = []

        rules: list[tuple[str, str, list[str], list[str]]] = [
            ("重试机制", "error_handling", ["重试", "retry"], ["fault-tolerance"]),
            ("缓存策略", "performance", ["缓存", "cache"], ["performance", "speed"]),
            ("并发处理", "performance", ["并发", "concurrent", "并行"], ["performance", "async"]),
            ("错误处理框架", "error_handling", ["错误处理", "exception", "error handling"], ["fault-tolerance"]),
            ("降级策略", "error_handling", ["降级", "fallback", "熔断"], ["fault-tolerance", "resilience"]),
            ("提示词模板", "prompt_design", ["提示词", "prompt template", "system prompt"], ["llm", "prompt"]),
            ("异步IO", "performance", ["async", "异步", "非阻塞"], ["performance", "io"]),
            ("数据校验", "accuracy", ["校验", "validate", "schema"], ["quality", "validation"]),
            ("日志记录", "observability", ["日志", "log", "logging"], ["observability"]),
            ("配置管理", "infrastructure", ["配置", "config", "setting"], ["infrastructure"]),
        ]

        for pattern_name, category, keywords, tags in rules:
            if any(kw in combined for kw in keywords):
                entry = self.add_or_update(
                    name=pattern_name,
                    category=category,
                    description=f"从技能 '{skill_name}' 自动提取的模式",
                    skill_name=skill_name,
                    tags=tags,
                )
                extracted.append(entry)

        return extracted

    def get_entry(self, name: str) -> PatternLibraryEntry | None:
        """获取单个模式条目"""
        return self._entries.get(name)

    def set_lifecycle(self, name: str, lifecycle: str) -> bool:
        """设置模式生命周期状态"""
        if lifecycle not in ("active", "deprecated", "archived"):
            return False
        with self._lock:
            entry = self._entries.get(name)
            if not entry:
                return False
            entry.lifecycle = lifecycle
            entry.updated_at = datetime.now()
        self._save()
        return True
