"""
SkillParser - 技能解析器
支持 YAML Frontmatter 和纯 Markdown 两种格式，含降级解析
"""

from __future__ import annotations

import re
from pathlib import Path

import frontmatter
from loguru import logger

from ..models import SkillMeta, SkillModule


# 技术栈关键词映射
TECH_STACK_KEYWORDS: dict[str, list[str]] = {
    "playwright": ["playwright", "browser", "page.goto", "page.click"],
    "cdp": ["cdp", "chrome devtools protocol", "devtools"],
    "python": ["python", "pip", "venv", "pytest", "asyncio"],
    "node": ["node", "npm", "yarn", "pnpm", "require("],
    "selenium": ["selenium", "webdriver"],
    "requests": ["requests", "httpx", "aiohttp"],
    "docker": ["docker", "dockerfile", "container"],
    "git": ["git ", "github", "gitlab"],
    "openai": ["openai", "gpt-", "chatgpt"],
    "anthropic": ["anthropic", "claude", "mcp"],
    "ollama": ["ollama", "qwen", "llama"],
    "fastapi": ["fastapi", "uvicorn"],
    "flask": ["flask", "werkzeug"],
    "pandas": ["pandas", "dataframe"],
    "numpy": ["numpy", "ndarray"],
    "sqlite": ["sqlite", "sqlalchemy"],
    "redis": ["redis"],
    "ffmpeg": ["ffmpeg"],
}

# 设计模式关键词
DESIGN_PATTERNS: dict[str, list[str]] = {
    "重试策略": ["retry", "重试", "backoff", "exponential"],
    "缓存策略": ["cache", "缓存", "ttl", "lru"],
    "并发控制": ["async", "await", "concurrent", "并发", "锁", "lock", "semaphore"],
    "错误处理": ["try", "except", "catch", "error handling", "错误处理"],
    "限流": ["rate limit", "限流", "throttle"],
    "批处理": ["batch", "批处理", "bulk"],
    "流水线": ["pipeline", "流水线", "chain"],
    "观察者": ["observer", "listener", "event", "hook", "回调"],
    "模板方法": ["template", "模板方法"],
    "策略模式": ["strategy", "策略模式"],
}

# 能力模块标题匹配模式
MODULE_TITLE_PATTERNS = [
    re.compile(r"^##+\s*(能力|模块|Capability|Module|Feature|Step|步骤)[:：\s]*(.+)$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^##+\s+(.+)$", re.MULTILINE),  # 所有二级/三级标题作为模块
]


class SkillParser:
    """技能解析器 - 多格式适配"""

    def __init__(self, fallback_to_llm: bool = False, frontmatter_schema: str = "claude"):
        self._fallback_to_llm = fallback_to_llm
        self._frontmatter_schema = frontmatter_schema

    def parse_file(self, file_path: str | Path, file_hash: str = "") -> SkillMeta:
        """
        解析 SKILL.md 文件。
        1. 尝试 Frontmatter 解析
        2. 降级为 Markdown 规则解析
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"技能文件不存在: {file_path}")

        raw_content = path.read_text(encoding="utf-8")
        return self.parse_content(raw_content, str(path.parent), file_hash)

    def parse_content(self, content: str, skill_path: str = "", file_hash: str = "") -> SkillMeta:
        """解析技能内容字符串"""
        # 尝试 Frontmatter 解析
        if content.strip().startswith("---"):
            try:
                return self._parse_with_frontmatter(content, skill_path, file_hash)
            except Exception as e:
                logger.warning(f"Frontmatter 解析失败，降级为规则解析: {e}")

        # 降级为纯 Markdown 解析
        return self._parse_markdown(content, skill_path, file_hash)

    def _parse_with_frontmatter(self, content: str, skill_path: str, file_hash: str) -> SkillMeta:
        """使用 python-frontmatter 解析"""
        post = frontmatter.loads(content)
        meta_dict = dict(post.metadata)
        body = post.content

        name = meta_dict.get("name", "")
        description = meta_dict.get("description", "")
        version = meta_dict.get("version", "1.0.0")
        author = meta_dict.get("author")

        # 从目录名推断技能名
        if not name and skill_path:
            name = Path(skill_path).name

        # 提取能力模块
        modules = self._extract_modules(body)

        # 提取技术栈
        tech_stack = self._extract_tech_stack(content)

        # 提取设计模式
        design_patterns = self._extract_design_patterns(content)

        return SkillMeta(
            name=name,
            description=description,
            version=str(version),
            author=author,
            tech_stack=tech_stack,
            modules=modules,
            raw_content=content,
            path=skill_path,
            hash=file_hash,
            frontmatter=meta_dict,
            design_patterns=design_patterns,
        )

    def _parse_markdown(self, content: str, skill_path: str, file_hash: str) -> SkillMeta:
        """纯 Markdown 规则解析（降级方案）"""
        lines = content.split("\n")

        # 提取一级标题作为技能名
        name = ""
        description = ""
        for i, line in enumerate(lines):
            if line.startswith("# ") and not name:
                name = line.lstrip("# ").strip()
                # 取标题下方第一段作为描述
                for j in range(i + 1, min(i + 10, len(lines))):
                    desc_line = lines[j].strip()
                    if desc_line and not desc_line.startswith("#"):
                        description = desc_line
                        break
                break

        # 从目录名推断
        if not name and skill_path:
            name = Path(skill_path).name

        # 提取能力模块
        modules = self._extract_modules(content)

        # 提取技术栈
        tech_stack = self._extract_tech_stack(content)

        # 提取设计模式
        design_patterns = self._extract_design_patterns(content)

        return SkillMeta(
            name=name or "unknown",
            description=description,
            version="1.0.0",
            author=None,
            tech_stack=tech_stack,
            modules=modules,
            raw_content=content,
            path=skill_path,
            hash=file_hash,
            frontmatter={},
            design_patterns=design_patterns,
        )

    def _extract_modules(self, content: str) -> list[SkillModule]:
        """从 Markdown 内容中提取能力模块"""
        modules: list[SkillModule] = []
        lines = content.split("\n")

        current_module: SkillModule | None = None
        current_lines: list[str] = []

        for line in lines:
            # 匹配二级或三级标题
            header_match = re.match(r"^(##+)\s+(.+)$", line)
            if header_match:
                # 保存上一个模块
                if current_module is not None:
                    current_module.raw_content = "\n".join(current_lines).strip()
                    modules.append(current_module)

                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                # 判断是否为能力模块标题
                is_module = bool(
                    re.search(
                        r"(能力|模块|Capability|Module|Feature|Step|步骤)",
                        title,
                        re.IGNORECASE,
                    )
                )

                current_module = SkillModule(
                    name=title,
                    description="",
                    dependencies=[],
                )
                current_lines = [line]

                # 如果不是明显的模块标题，至少记录标题
                if not is_module and level <= 2:
                    # 二级标题都作为模块
                    pass

            elif current_module is not None:
                current_lines.append(line)
                # 提取第一段作为描述
                if not current_module.description and line.strip() and not line.startswith("#"):
                    current_module.description = line.strip()

        # 保存最后一个模块
        if current_module is not None:
            current_module.raw_content = "\n".join(current_lines).strip()
            modules.append(current_module)

        # 为模块提取依赖
        for module in modules:
            module.dependencies = self._extract_tech_stack(module.raw_content)

        return modules

    def _extract_tech_stack(self, content: str) -> list[str]:
        """从内容中提取技术栈关键词"""
        content_lower = content.lower()
        found: list[str] = []
        for tech, keywords in TECH_STACK_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in content_lower:
                    if tech not in found:
                        found.append(tech)
                    break
        return found

    def _extract_design_patterns(self, content: str) -> list[str]:
        """从内容中提取设计模式标签"""
        content_lower = content.lower()
        found: list[str] = []
        for pattern, keywords in DESIGN_PATTERNS.items():
            for kw in keywords:
                if kw.lower() in content_lower:
                    if pattern not in found:
                        found.append(pattern)
                    break
        return found
