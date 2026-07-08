# Skill Composer MCP — 介绍

## 这是什么

一个本地运行的 **AI 技能组合器**。它能读取、分析、对比和组合多个 SKILL.md 技能文件，让不同的 AI 技能像乐高积木一样拼接使用。

**核心原则**：所有原始技能文件**只读不写**，永不污染源文件。

## 关键内容

### 13 个 MCP 工具

| 工具 | 一句话说明 |
|---|---|
| `configure_skills` | 首次使用配置技能目录 |
| `list_skills` | 列出/搜索所有技能 |
| `analyze_skill` | **六维分析**（速度/准确度/鲁棒性/输出质量/提示策略/工具使用）+ 逆向工程 |
| `compare_skills` | 两个技能差异对比 + 六维雷达图 |
| `compose_skills` | 组合技能（diff/temp/persist/dry-run） |
| `recommend_combo` | AI 自动推荐最佳组合方案 |
| `save_template` / `load_template` / `list_templates` | 模板管理 |
| `search_patterns` | 搜索模式库（成功率/分类/标签） |
| `analyze_evolution` | 进化分析（六维差异 + 路线图） |
| `progressive_inject` | **逐维度渐进注入**，一步一确认 |
| `approve_step` / `reject_step` | 注入步骤决策 |
| `reload_config` | 手动热加载配置 |

### 六维评估框架

每个技能从 6 个维度打分（0-10），生成雷达图：

```
speed          ─ 执行效率与性能
accuracy       ─ 校验与精确度
robustness     ─ 错误处理与容错
output_quality ─ 输出结构化与可读性
prompt_strategy─ 提示词设计策略
tool_usage     ─ 工具调用与编排
```

### 模式库

从技能中自动提取可复用设计模式，持久化到 `~/.composed_skills/pattern-library.json`，追踪每次使用的成功/失败和生命周期。

## 使用方法

### 1. 安装

```bash
git clone https://github.com/K-Host/skill-composer-mcp.git
cd skill-composer-mcp
uv sync
```

### 2. 配置 MCP 客户端

在 opencode.json 或 MCP 客户端配置文件中添加：

```json
{
  "mcp": {
    "skill-composer": {
      "type": "local",
      "command": ["uv", "run", "python", "-m", "skill_composer_mcp"],
      "enabled": true
    }
  }
}
```

### 3. 首次引导

启动后调用 `configure_skills` 告诉工具去哪找你的技能文件：

```
configure_skills(skill_paths=[
  "~/.config/opencode/skills",
  "./skills"
])
```

### 4. 在对话中使用

配置完成后直接说：

- *"列出所有技能"*
- *"分析一下 xxx 技能"*
- *"对比 A 和 B"*
- *"把 A 和 B 组合起来"*

## 融合方法参考

本项目六维评估框架、模式库提取、渐进式注入等核心技术受 [Taotie Skill](https://github.com/binggandata/bggg-skill-taotie) 启发。Taotie 是一套开源的技能进化框架，提供了技能质量评估、模式复用和持续优化的完整方法论，推荐参考。

## 项目结构

```
├── 介绍.md          ← 本文档
├── opencode.json    ← MCP 客户端配置
├── pyproject.toml   ← 项目依赖
├── src/
│   └── skill_composer_mcp/
│       ├── server.py          # MCP 协议层（13 个工具）
│       ├── config.py          # 配置 + 热加载
│       ├── models.py          # 数据模型
│       └── core/
│           ├── skill_loader.py     # 技能扫描
│           ├── skill_parser.py     # 技能解析
│           ├── skill_analyzer.py   # 六维分析 + 逆向工程
│           ├── skill_composer.py   # 组合引擎 + 渐进注入
│           ├── pattern_library.py  # 持久化模式库
│           ├── security_guard.py   # 安全沙箱
│           ├── template_manager.py # 模板管理
│           └── llm_factory.py      # LLM 封装
├── skills/          ← 自定义技能目录
└── examples/        ← 示例技能
```
