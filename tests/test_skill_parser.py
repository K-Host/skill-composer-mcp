"""
SkillParser 技能解析器测试
"""

import pytest

from skill_composer_mcp.core.skill_parser import SkillParser


@pytest.fixture
def parser():
    return SkillParser(fallback_to_llm=False)


FRONTMATTER_CONTENT = """---
name: test-skill
description: A test skill
version: 1.0.0
author: tester
tags:
  - test
---

# test-skill

This is a test skill.

## 能力：搜索

Search capability.

Uses requests library.

## 模块：缓存

Cache module with redis.

## Module: Export

Export data to CSV.
"""

MARKDOWN_CONTENT = """# markdown-skill

A skill without frontmatter.

## 能力：分析

Analysis module.

Uses pandas and numpy.

## 模块：输出

Output generation.
"""


class TestSkillParser:
    def test_parse_frontmatter(self, parser):
        """测试 Frontmatter 解析"""
        meta = parser.parse_content(FRONTMATTER_CONTENT, "/path/to/skill", "abc123")
        assert meta.name == "test-skill"
        assert meta.description == "A test skill"
        assert meta.version == "1.0.0"
        assert meta.author == "tester"
        assert meta.hash == "abc123"
        assert "name" in meta.frontmatter
        assert meta.frontmatter["name"] == "test-skill"

    def test_parse_markdown_only(self, parser):
        """测试纯 Markdown 解析"""
        meta = parser.parse_content(MARKDOWN_CONTENT, "/path/to/skill")
        assert meta.name == "markdown-skill"
        assert meta.description == "A skill without frontmatter."
        assert meta.frontmatter == {}

    def test_extract_modules(self, parser):
        """测试能力模块提取"""
        meta = parser.parse_content(FRONTMATTER_CONTENT, "/path/to/skill")
        module_names = [m.name for m in meta.modules]
        assert "能力：搜索" in module_names or any("搜索" in n for n in module_names)
        assert "模块：缓存" in module_names or any("缓存" in n for n in module_names)

    def test_extract_tech_stack(self, parser):
        """测试技术栈提取"""
        meta = parser.parse_content(FRONTMATTER_CONTENT, "/path/to/skill")
        assert "requests" in meta.tech_stack
        assert "redis" in meta.tech_stack

    def test_extract_design_patterns(self, parser):
        """测试设计模式提取"""
        content = """
        # Skill

        ## 模块：重试

        Retry with exponential backoff.
        Use cache for performance.
        """
        meta = parser.parse_content(content, "/path/to/skill")
        assert "重试策略" in meta.design_patterns
        assert "缓存策略" in meta.design_patterns

    def test_infer_name_from_path(self, parser):
        """测试从路径推断技能名（无标题时）"""
        content = "Some content without title"
        meta = parser.parse_content(content, "/path/to/my-skill")
        assert meta.name == "my-skill"

    def test_raw_content_preserved(self, parser):
        """测试原始内容保留"""
        meta = parser.parse_content(FRONTMATTER_CONTENT, "/path/to/skill")
        assert "test-skill" in meta.raw_content
        assert "搜索" in meta.raw_content
