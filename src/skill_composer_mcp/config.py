"""
配置系统 - 支持 .env、环境变量、YAML 配置文件和代码默认值
优先级（从高到低）：代码直接配置 > YAML配置文件 > 环境变量 > .env文件 > 默认值

热加载：ConfigFile 检查文件 mtime，每次调用时自动重读变更。
首次引导：检测到无技能路径且无环境变量覆盖时，提示用户调用 configure_skills 工具。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = "~/.skill-composer"
CONFIG_FILE = "config.yaml"


class ConfigFile:
    """可读写的 YAML 配置文件，支持热加载检测"""

    def __init__(self) -> None:
        self._dir = Path(os.path.expanduser(CONFIG_DIR))
        self._path = self._dir / CONFIG_FILE
        self._mtime: float = 0
        self._cached: dict[str, Any] = {}
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> dict[str, Any]:
        """加载配置文件，带 mtime 缓存"""
        current_mtime = self._get_mtime()
        if current_mtime == self._mtime and self._cached:
            return self._cached
        if not self._path.exists():
            self._cached = {}
            self._mtime = 0
            return {}
        with open(self._path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self._cached = data
        self._mtime = current_mtime
        return data

    def save(self, data: dict[str, Any]) -> None:
        """写入配置文件"""
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
        self._cached = dict(data)
        self._mtime = self._get_mtime()

    def _get_mtime(self) -> float:
        if self._path.exists():
            return self._path.stat().st_mtime
        return 0

    def changed_since(self, since: float) -> bool:
        """检测配置文件是否自 since 时间后发生过变更"""
        return self._get_mtime() > since

    def needs_setup(self) -> bool:
        """是否需要首次引导：没有 skill_paths 且没有 SKILLS_PATHS 环境变量"""
        if os.environ.get("SKILLS_PATHS", "").strip():
            return False
        data = self.load()
        paths = data.get("skill_paths", [])
        return len(paths) == 0


class SecurityConfig(BaseModel):
    """安全配置"""

    allow_read_only: bool = True
    allowed_roots: list[str] = Field(default_factory=list)
    forbidden_dirs: list[str] = Field(
        default_factory=lambda: ["/etc", "/usr", "/root/.ssh", "~/.ssh"]
    )


class ParserConfig(BaseModel):
    """解析器配置"""

    fallback_to_llm: bool = False
    frontmatter_schema: str = "claude"  # claude / generic


class OutputConfig(BaseModel):
    """输出配置"""

    default_mode: str = "diff"  # diff / temp / persist
    max_history: int = 20
    storage_dir: str = "./composed_skills"


class LLMConfig(BaseModel):
    """LLM 配置"""

    provider: str = "ollama"  # openai / anthropic / ollama
    api_key: str | None = None
    model: str = "qwen2.5:7b"
    base_url: str | None = None


class AppConfig(BaseModel):
    """应用主配置"""

    skill_paths: list[str] = Field(default_factory=list)
    composed_skills_dir: str = "./composed_skills"
    pattern_library_path: str = "./composed_skills/pattern-library.json"
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    parser: ParserConfig = Field(default_factory=ParserConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)


def _default_skill_paths(config_file: ConfigFile | None = None) -> list[str]:
    """获取技能搜索路径，优先级：环境变量 > 配置文件 > 默认值"""
    # 1. 环境变量最高优先级
    env_paths = os.environ.get("SKILLS_PATHS", "")
    if env_paths:
        sep = ";" if ";" in env_paths else ":"
        return [p.strip() for p in env_paths.split(sep) if p.strip()]

    # 2. 配置文件
    if config_file is not None:
        data = config_file.load()
        paths = data.get("skill_paths", [])
        if paths:
            return paths

    # 3. 默认值（首次安装时为空，触发引导流程）
    return []


def _find_yaml_config() -> Path | None:
    """查找项目级 YAML 配置文件"""
    candidates = [
        Path.cwd() / ".skill-composer" / "config.yaml",
        Path.cwd() / ".skill-composer" / "config.yml",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _load_yaml_config(yaml_path: Path) -> dict[str, Any]:
    """加载 YAML 配置文件"""
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(config_file: ConfigFile | None = None, **overrides: Any) -> AppConfig:
    """
    加载配置，合并多个来源。
    优先级：代码overrides > 项目YAML > 环境变量 > ConfigFile > 默认值

    若返回的 AppConfig.skill_paths 为空，表示首次使用需要引导。
    """
    if config_file is None:
        config_file = ConfigFile()

    # 1. 默认值 + 环境变量
    skill_paths = _default_skill_paths(config_file)
    composed_dir = os.environ.get(
        "SKILL_COMPOSER_COMPOSED_SKILLS_DIR",
        os.environ.get("COMPOSED_SKILLS_DIR", "./composed_skills"),
    )

    config_data: dict[str, Any] = {
        "skill_paths": skill_paths,
        "composed_skills_dir": composed_dir,
    }

    # LLM 配置从环境变量
    llm_provider = os.environ.get("SKILL_COMPOSER_LLM_PROVIDER", "ollama")
    llm_api_key = os.environ.get("SKILL_COMPOSER_LLM_API_KEY")
    llm_model = os.environ.get(
        "SKILL_COMPOSER_LLM_MODEL",
        "gpt-4o-mini" if llm_provider == "openai" else "qwen2.5:7b",
    )
    llm_base_url = os.environ.get("SKILL_COMPOSER_LLM_BASE_URL")

    config_data["llm"] = {
        "provider": llm_provider,
        "api_key": llm_api_key,
        "model": llm_model,
        "base_url": llm_base_url,
    }

    # 输出配置从环境变量
    output_mode = os.environ.get("SKILL_COMPOSER_OUTPUT_DEFAULT_MODE", "diff")
    config_data["output"] = {"default_mode": output_mode}

    # 解析器配置从环境变量
    fallback_llm = os.environ.get("SKILL_COMPOSER_PARSER_FALLBACK_TO_LLM", "false")
    config_data["parser"] = {"fallback_to_llm": fallback_llm.lower() == "true"}

    # 2. 项目级 YAML 配置覆盖（只读，不参与热加载）
    yaml_path = _find_yaml_config()
    if yaml_path:
        yaml_data = _load_yaml_config(yaml_path)
        for key, val in yaml_data.items():
            if key in ("security", "parser", "output", "llm") and isinstance(val, dict):
                if key not in config_data:
                    config_data[key] = {}
                config_data[key].update(val)
            else:
                config_data[key] = val

    # 3. 代码 overrides 最高优先级
    for key, val in overrides.items():
        if key in ("security", "parser", "output", "llm") and isinstance(val, dict):
            if key not in config_data:
                config_data[key] = {}
            config_data[key].update(val)
        else:
            config_data[key] = val

    # 确保 allowed_roots 包含 skill_paths 和 composed_skills_dir
    if not config_data.get("security", {}).get("allowed_roots"):
        security_data = config_data.get("security", {})
        security_data["allowed_roots"] = list(config_data["skill_paths"])
        security_data["allowed_roots"].append(config_data["composed_skills_dir"])
        config_data["security"] = security_data

    return AppConfig(**config_data)
