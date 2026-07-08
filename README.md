# Skill Composer MCP

> 本地MCP技能组合器 — 基于MCP协议的AI技能动态组合工具

一个运行在本地、基于 MCP（Model Context Protocol）协议的 AI 技能动态组合工具。它能够在**不修改任何原有技能文件**的前提下，按需读取、分析和组合多个 SKILL.md（技能描述文档），生成临时或持久的融合技能。

## 核心特性

| 特性 | 说明 |
|---|---|
| **零修改** | 所有原始技能保持只读，永不污染 |
| **按需组合** | 在 AI 对话中通过自然语言动态触发组合 |
| **跨平台兼容** | 任何支持 MCP 协议的 Agent 均可使用（opencode、Claude Code、Cursor、Cline、Windsurf 等） |
| **差异可见** | 组合前返回结构化差异清单，用户确认后再落盘 |
| **安全沙箱** | 严格路径白名单，禁止越权读取和写入 |
| **AI 辅助决策** | 支持 LLM 推荐最佳技能组合方案（Ollama/OpenAI/Anthropic） |
| **模糊搜索** | 支持中英文语义匹配，如搜"小红书"匹配到 `xiaohongshu-skill` |
| **热加载配置** | 修改配置文件后无需重启服务，自动检测并重载 |
| **首次引导** | 第一次使用自动提示配置技能目录，交互式完成初始化 |

## MCP 工具（共 10 个）

| 工具 | 必需参数 | 可选参数 | 功能 |
|---|---|---|---|
| `list_skills` | — | `query` | 列出所有本地技能（支持模糊搜索） |
| `analyze_skill` | `skill_name` | — | 深度分析指定技能（能力模块、技术栈、设计模式） |
| `compare_skills` | `base_skill`, `candidate_skill` | — | 对比两个技能的差异 |
| `compose_skills` | `base`, `additions` | `output_mode`, `dry_run`, `conflict_choices` | 组合多个技能 |
| `recommend_combo` | `task` | `llm_provider` | 根据任务描述自动推荐最佳组合 |
| `save_template` | `template_name`, `base_skill`, `additions` | `description` | 保存组合模板 |
| `load_template` | `template_name` | — | 加载已保存的模板 |
| `list_templates` | — | — | 列出所有已保存的模板 |
| `configure_skills` | `skill_paths` | — | 配置技能目录路径（首次引导），保存后自动热加载 |
| `reload_config` | — | — | 手动重新加载配置文件 |

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 可选：安装 LLM 支持（本地 Ollama / 云端 OpenAI / Anthropic）
uv sync --extra llm
uv sync --extra ollama

# 使用 pip
pip install -e .
pip install -e ".[ollama]"
```

### 2. 配置 MCP 客户端

#### opencode

```json
{
  "mcp": {
    "skill-composer": {
      "type": "local",
      "command": ["uv", "run", "python", "-m", "skill_composer_mcp"],
      "enabled": true,
      "env": {
        "SKILL_COMPOSER_LLM_PROVIDER": "ollama"
      }
    }
  }
}
```

#### Claude Code / Cursor 等

```json
{
  "mcpServers": {
    "skill-composer": {
      "command": "uv",
      "args": ["run", "python", "-m", "skill_composer_mcp"],
      "env": {
        "SKILL_COMPOSER_LLM_PROVIDER": "ollama"
      }
    }
  }
}
```

### 3. 首次使用（配置技能目录）

启动后，调用 `list_skills` 会提示配置技能路径。使用 `configure_skills` 工具设置：

```
configure_skills(skill_paths=[
  "~/.config/opencode/skills",
  "./skills",
  "./examples/skills"
])
```

配置会自动保存到 `~/.skill-composer/config.yaml`，后续可直接编辑该文件。

### 4. 在对话中使用

配置完成后，你可以通过 AI 对话使用所有功能：

- *"帮我列出所有可用的技能"*
- *"分析一下 research-skill 这个技能"*
- *"对比 research-skill 和 writer-skill 的差异"*
- *"把 research-skill 和 xiaohongshu-skill 组合起来"*
- *"我需要做学术研究并写小红书笔记，推荐一个技能组合"*

## 输出模式

`compose_skills` 工具支持四种输出模式：

| 模式 | 说明 | 适用场景 |
|---|---|---|
| **diff**（默认） | 仅返回结构化差异清单，不生成完整内容 | 所有组合操作的首选模式，Token 消耗低 |
| **temp** | 返回完整 SKILL.md 内容，不落盘 | 用户确认 diff 后立即使用 |
| **persist** | 保存到 `~/.composed_skills/` 隔离目录 | 长期使用组合技能 |
| **dry-run** | 仅返回冲突报告和差异摘要 | 决策前的信息获取 |

## 配置文件

### ~/.skill-composer/config.yaml（主配置文件）

首次使用 `configure_skills` 后自动生成。支持热加载——修改后下次工具调用自动生效，无需重启。

```yaml
skill_paths:
  - C:\Users\xxx\.config\opencode\skills
  - .\skills
  - .\examples\skills
```

### .skill-composer/config.yaml（项目级，只读）

项目根目录下的 `.skill-composer/config.yaml`（可选），用于覆盖安全策略、输出模式和 LLM 配置。不会参与热加载。

```yaml
security:
  allow_read_only: true
  allowed_roots:
    - "./skills"
  forbidden_dirs:
    - "/etc"
    - "/usr"
    - "~/.ssh"

output:
  default_mode: "diff"

llm:
  provider: "ollama"
  model: "qwen2.5:7b"

parser:
  fallback_to_llm: false
  frontmatter_schema: "claude"
```

### opencode.json（opencode MCP 配置）

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "skill-composer": {
      "type": "local",
      "command": ["uv", "run", "python", "-m", "skill_composer_mcp"],
      "enabled": true,
      "env": {
        "SKILL_COMPOSER_LLM_PROVIDER": "ollama"
      }
    }
  }
}
```

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `SKILLS_PATHS` | — | 技能搜索路径（最高优先级，覆盖配置文件） |
| `SKILL_COMPOSER_LLM_PROVIDER` | `ollama` | LLM 提供商（ollama/openai/anthropic） |
| `SKILL_COMPOSER_LLM_MODEL` | `qwen2.5:7b` | LLM 模型名称 |
| `SKILL_COMPOSER_LLM_API_KEY` | — | API 密钥（仅云端 LLM 需要） |
| `SKILL_COMPOSER_LLM_BASE_URL` | — | 自定义 API 地址 |
| `SKILL_COMPOSER_OUTPUT_DEFAULT_MODE` | `diff` | 默认输出模式 |
| `SKILL_COMPOSER_PARSER_FALLBACK_TO_LLM` | `false` | 解析失败时是否调用 LLM 辅助 |

## 文件输出位置

| 路径 | 说明 |
|---|---|
| `~/.skill-composer/config.yaml` | 技能路径配置文件（可读写，热加载） |
| `~/.composed_skills/` | `persist` 模式的组合技能输出目录 |
| `~/.composed_skills/templates/` | 组合模板存储目录（JSON 格式） |
| `./skills/` | 项目自定义技能目录（放置 SKILL.md） |
| `./examples/skills/` | 项目示例技能目录 |

## 技能文件格式（SKILL.md）

技能是遵循以下格式的 Markdown 文件：

```markdown
---
name: my-skill
description: 技能描述
version: 1.0.0
author: author-name
tags:
  - tag1
  - tag2
---

# my-skill

技能详细说明...

## 能力：xxx

能力描述...

- 要点1
- 要点2

技术依赖：xxx

## 模块：xxx

模块描述...

### 子模块
```

SKILL.md 放在 `skills/<技能名>/` 目录下。

## 安全机制

- **路径白名单沙箱** — 所有文件访问必经 `SecurityGuard` 校验
- **写入隔离** — `persist` 模式只能写入 `~/.composed_skills/` 隔离目录
- **哈希校验** — 写入前检查目标文件是否存在，防止误覆盖
- **防路径遍历** — 解析符号链接后二次校验白名单

## 项目结构

```
skill-composer-mcp/
├── opencode.json              # opencode MCP 配置
├── pyproject.toml             # 项目元数据与依赖
├── uv.lock                    # uv 依赖锁定文件
├── .env.example               # 环境变量模板
│
├── src/skill_composer_mcp/
│   ├── __init__.py            # 包版本
│   ├── __main__.py            # python -m 入口
│   ├── server.py              # MCP Server（10个工具注册）
│   ├── config.py              # 配置系统（ConfigFile + 热加载）
│   ├── models.py              # Pydantic 数据模型
│   │
│   ├── core/
│   │   ├── security_guard.py  # 安全沙箱（路径白名单/黑名单）
│   │   ├── skill_loader.py    # 技能扫描加载器（带缓存）
│   │   ├── skill_parser.py    # 多格式解析器（YAML frontmatter + Markdown）
│   │   ├── skill_analyzer.py  # 技能分析器（模块/技术栈/设计模式）
│   │   ├── skill_composer.py  # 组合引擎（冲突检测 + 融合）
│   │   ├── template_manager.py # 模板管理（保存/加载/列表）
│   │   └── llm_factory.py     # LLM 工厂（Ollama/OpenAI/Anthropic）
│   │
│   └── utils/
│       └── fuzzy_matcher.py   # 模糊匹配（中英文语义）
│
├── tests/                     # 单元测试
│   ├── test_security_guard.py
│   ├── test_skill_loader.py
│   ├── test_skill_parser.py
│   ├── test_skill_analyzer.py
│   ├── test_skill_composer.py
│   └── test_template_manager.py
│
├── examples/
│   ├── skills/                # 示例技能
│   │   ├── research-skill/    # 学术研究技能
│   │   ├── writer-skill/      # AI写作技能
│   │   └── xiaohongshu-skill/ # 小红书内容创作技能
│   └── config.yaml.example    # 项目级配置示例
│
└── skills/                    # 自定义技能
    ├── weather-wttr/          # 命令行天气查询（wttr.in）
    └── weather-openweather/   # OpenWeatherMap 专业天气查询
```

## 技能示例

项目自带 5 个技能供参考：

| 技能名 | 来源 | 说明 |
|---|---|---|
| research-skill | `examples/skills/` | 学术研究辅助（文献检索、分析、综述撰写） |
| writer-skill | `examples/skills/` | AI 写作辅助（多风格创作、润色、SEO） |
| xiaohongshu-skill | `examples/skills/` | 小红书内容创作（笔记、图片、发布管理） |
| weather-wttr | `skills/` | 命令行天气查询（curl wttr.in，零配置） |
| weather-openweather | `skills/` | 专业天气查询（OpenWeatherMap API，需注册 Key） |

## 开发

```bash
# 安装开发依赖
uv sync --group dev

# 运行测试
pytest tests/ -v

# 运行覆盖率
pytest --cov=skill_composer_mcp tests/

# 运行简化模式（不依赖 MCP 客户端，直接命令行交互）
uv run python -m skill_composer_mcp
```

## License

MIT
