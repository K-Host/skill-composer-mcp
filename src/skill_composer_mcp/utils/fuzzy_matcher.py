"""
模糊语义匹配工具
使用 difflib 或 fuzzywuzzy 对技能名和描述进行打分
"""

from __future__ import annotations

import difflib
from typing import Any

try:
    from fuzzywuzzy import fuzz, process

    HAS_FUZZYWUZZY = True
except ImportError:
    HAS_FUZZYWUZZY = False


class FuzzyMatcher:
    """模糊匹配器"""

    def __init__(self, use_fuzzywuzzy: bool = True):
        self._use_fuzzy = use_fuzzywuzzy and HAS_FUZZYWUZZY

    def search(
        self,
        query: str,
        candidates: list[dict[str, str]],
        key_fields: list[str] | None = None,
        limit: int = 5,
        min_score: int = 40,
    ) -> list[dict[str, Any]]:
        """
        模糊搜索。

        Args:
            query: 搜索关键词
            candidates: 候选项列表，每个项是 dict
            key_fields: 参与匹配的字段列表（默认 ["name", "description"]）
            limit: 返回前 N 个结果
            min_score: 最低匹配分数

        Returns:
            排序后的匹配结果列表，包含 score 和原始数据
        """
        if key_fields is None:
            key_fields = ["name", "description"]

        results: list[dict[str, Any]] = []

        for item in candidates:
            best_score = 0
            matched_field = ""

            for field in key_fields:
                text = item.get(field, "")
                if not text:
                    continue

                score = self._score(query, text)
                if score > best_score:
                    best_score = score
                    matched_field = field

            if best_score >= min_score:
                results.append(
                    {
                        **item,
                        "score": best_score,
                        "matched_field": matched_field,
                    }
                )

        # 按分数降序排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def _score(self, query: str, text: str) -> int:
        """计算匹配分数（0-100）"""
        query_lower = query.lower().strip()
        text_lower = text.lower().strip()

        if not query_lower or not text_lower:
            return 0

        # 精确匹配
        if query_lower == text_lower:
            return 100

        if self._use_fuzzy:
            # 使用 fuzzywuzzy
            ratio = fuzz.partial_ratio(query_lower, text_lower)
            return int(ratio)
        else:
            # 使用 difflib
            ratio = difflib.SequenceMatcher(None, query_lower, text_lower).ratio()
            return int(ratio * 100)

    def best_match(
        self, query: str, candidates: list[str]
    ) -> str | None:
        """返回最佳匹配项"""
        if not candidates:
            return None

        if self._use_fuzzy:
            result = process.extractOne(query, candidates, scorer=fuzz.partial_ratio)
            if result and result[1] >= 40:
                return result[0]
        else:
            matches = difflib.get_close_matches(query, candidates, n=1, cutoff=0.4)
            if matches:
                return matches[0]

        # 最后尝试包含匹配
        query_lower = query.lower()
        for c in candidates:
            if query_lower in c.lower():
                return c

        return None
