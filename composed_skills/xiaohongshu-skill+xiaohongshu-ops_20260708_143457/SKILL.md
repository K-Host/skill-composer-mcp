---
name: xiaohongshu-skill+xiaohongshu-ops
description: 组合技能 - 基础: xiaohongshu-skill, 融合: xiaohongshu-ops
version: 2.0.0
author: skill-composer-mcp
composed_at: 2026-07-08T14:34:57.781517
source_hashes:
  xiaohongshu-skill: 3784f7fd6b015ff2b04ff6588a0550a1e001ad2287fb8a17512e51a4238efbea
  xiaohongshu-ops: 5f19d95f9aa68cd09eeb0c64e23ce3db9eda23be60a447ecdec4b88cc5a19f09
---

# xiaohongshu-skill + xiaohongshu-ops

> 本技能由 skill-composer-mcp 自动组合生成
> 基础技能: xiaohongshu-skill
> 融合技能: xiaohongshu-ops
> 生成时间: 2026-07-08 14:34:57

# 小红书 Skill

用 Python Playwright 驱动浏览器操作小红书。数据从 `window.__INITIAL_STATE__`（Vue SSR 状态对象）里取。搜索、发布、互动、运营全在这。

## 写操作安全规则

下面这些命令会真的改动账号数据。跑之前**必须**让用户确认：

1. **发布笔记** -- 先展示标题、正文、图片列表。用户说"发"才发。
2. **评论/回复** -- 先展示要发出去的内容。用户说"发"才发。
3. **点赞/收藏** -- 先展示目标帖子。用户说"行"才执行。

用 `AskUserQuestion` 弹确认框。别自己决定。

## 前置条件

在 `{baseDir}` 目录装依赖：

```bash
cd {baseDir}
pip install -r requirements.txt
playwright install chromium
```

Linux/WSL 还要跑：

```bash
playwright install-deps chromium
```

## 快速开始

所有命令从 `{baseDir}` 目录跑。

### 1. 登录（第一次必须做）

```bash
cd {baseDir}

# 弹出浏览器窗口，显示二维码，用微信或小红书 App 扫
python -m scripts qrcode --headless=false

# 检查登录还在不在
python -m scripts check-login
```

无头环境里二维码存到 `{baseDir}/data/qrcode.png`。传给别人扫也行。

### 2. 搜索

```bash
cd {baseDir}

# 基本搜索
python -m scripts search "关键词"

# 带条件
python -m scripts search "美食" --sort-by=最新 --note-type=图文 --limit=10
```

**筛选选项：**

- `--sort-by`：综合、最新、最多点赞、最多评论、最多收藏
- `--note-type`：不限、视频、图文
- `--publish-time`：不限、一天内、一周内、半年内
- `--search-scope`：不限、已看过、未看过、已关注
- `--location`：不限、同城、附近

### 3. 帖子详情

```bash
cd {baseDir}

# 用搜索结果里的 id 和 xsec_token
python -m scripts feed <feed_id> <xsec_token>

# 同时加载评论
python -m scripts feed <feed_id> <xsec_token> --load-comments --max-comments=20
```

### 4. 用户主页

```bash
cd {baseDir}

# 看别人的主页
python -m scripts user <user_id> [xsec_token]

# 看自己的主页
python -m scripts me
```

### 5. 评论互动

**先确认再发。** 跑之前用 `AskUserQuestion` 把评论内容亮出来让用户确认。

```bash
cd {baseDir}

# 发评论
python -m scripts comment <feed_id> <xsec_token> --content="好棒的笔记！"

# 回复别人的评论
python -m scripts reply <feed_id> <xsec_token> --comment-id=<comment_id> --reply-user-id=<user_id> --content="感谢分享"

# 通过通知页回复（更安全）
python -m scripts reply-notification --content="谢谢关注" --index=0
```

### 6. 点赞 / 收藏

**先确认再操作。** 用 `AskUserQuestion` 把目标帖子亮出来让用户确认。

```bash
cd {baseDir}

# 点赞 / 取消
python -m scripts like <feed_id> <xsec_token>
python -m scripts unlike <feed_id> <xsec_token>

# 收藏 / 取消
python -m scripts collect <feed_id> <xsec_token>
python -m scripts uncollect <feed_id> <xsec_token>
```

### 7. 首页推荐流

```bash
cd {baseDir}
python -m scripts explore --limit=20
```

### 8. 发布笔记

**先确认再发。** 跑之前用 `AskUserQuestion` 把标题、正文、图片亮出来让用户确认。

```bash
cd {baseDir}

# 图文笔记（默认停在发布按钮，加 --auto-publish 自动发）
python -m scripts publish --title="标题" --content="正文" --images="img1.jpg,img2.jpg" --tags="旅行,美食"

# 视频笔记
python -m scripts publish-video --title="标题" --content="描述" --video="video.mp4" --tags="vlog"

# Markdown 渲染成图片再发
python -m scripts publish-md --title="标题" --file=article.md --tags="干货"
python -m scripts publish-md --title="标题" --text="# 正文\n内容..." --width=1080

# 长文笔记（创作者中心"写长文"）
python -m scripts publish-longform --title="长文标题" --content="长文正文内容..."

# 定时发布
python -m scripts publish --title="标题" --content="正文" --images="img.jpg" --schedule-time="2025-03-01 12:00"
```

### 9. 写作模板

```bash
cd {baseDir}

# 生成模板（标题建议 + 内容框架 + 标签推荐）
python -m scripts template --topic="旅行攻略"
python -m scripts template --topic="美食探店" --type=视频
python -m scripts template --topic="学习方法" --type=长文
```

### 10. 运营策略

```bash
cd {baseDir}

# 设账号定位
python -m scripts strategy-init --persona="旅行博主" --audience="18-35岁旅行爱好者" --direction="旅行攻略,小众目的地"

# 看当前策略
python -m scripts strategy-show

# 查今日互动配额
python -m scripts strategy-check-limit --limit-type=likes
python -m scripts strategy-check-limit --limit-type=comments

# 加内容日历
python -m scripts strategy-add-post --date="2025-03-01" --topic="春日出行攻略" --type=图文
```

### 11. SOP 编排

```bash
cd {baseDir}

# 发布 SOP（选题分析 -> 内容校验 -> 模板生成 -> 发布准备）
python -m scripts sop --type=publish --topic="旅行攻略" --note-type=图文

# 推荐流互动 SOP（模拟真人浏览行为）
python -m scripts sop --type=explore --feed-count=10 --like-prob=0.3 --collect-prob=0.1

# 评论互动 SOP（逐条回复，带配额控制）
python -m scripts sop --type=comment --replies='[{"feed_id":"abc","xsec_token":"xyz","content":"好棒"}]'
```

## 数据提取路径

| 数据类型 | JavaScript 路径 |
|----------|----------------|
| 搜索结果 | `window.__INITIAL_STATE__.search.feeds` |
| 帖子详情 | `window.__INITIAL_STATE__.note.noteDetailMap` |
| 互动状态 | `window.__INITIAL_STATE__.note.noteDetailMap[id].note.interactInfo` |
| 用户信息 | `window.__INITIAL_STATE__.user.userPageData` |
| 用户笔记 | `window.__INITIAL_STATE__.user.notes` |
| 推荐流   | `window.__INITIAL_STATE__.feed.feeds` |

**Vue Ref 解包：** 始终用 `.value` 或 `._value`：

```javascript
const data = obj.value !== undefined ? obj.value : obj._value;
```

## 反爬保护

内置多层防护，尽量避免触发验证码：

- **频率控制**：两次导航间自动等 3-6 秒。连续 5 次请求后冷却 10 秒。
- **真人化延迟**：点击前等 1-2.5s，点击后冷却 5-12s。每 3 次交互批次冷却 15-30s。
- **真人化发布**：标题填写延迟 0.5-1.5s。正文逐字输入，每字 20-60ms。步骤间隔随机。
- **频率检测**：自动识别 toast 提示（"频繁"、"操作太快"、"稍后再试"）。
- **失败重试**：评论提交失败自动重试一次（间隔 2-4s）。
- **验证码检测**：检测到安全验证重定向时抛出 `CaptchaError`。
- **每日配额**：策略模块追踪每天互动次数，防止超。

**触发验证码了怎么办：**

1. 等几分钟再试。
2. 跑 `cd {baseDir} && python -m scripts qrcode --headless=false` 手动过验证。
3. Cookie 失效了就重新扫码登录。

## 输出格式

所有命令输出 JSON。搜索结果长这样：

```json
{
  "id": "abc123",
  "xsec_token": "ABxyz...",
  "title": "帖子标题",
  "type": "normal",
  "user": "用户名",
  "user_id": "user123",
  "liked_count": "1234",
  "collected_count": "567",
  "comment_count": "89"
}
```

## 文件结构

```
{baseDir}/
├── SKILL.md              # 本文件
├── README.md             # 项目文档
├── requirements.txt      # Python 依赖
├── LICENSE               # MIT
├── data/                 # 运行时数据（二维码、调试输出）
├── scripts/              # 核心模块
│   ├── __init__.py       # 模块导出（v1.3.0）
│   ├── __main__.py       # CLI 入口（22+ 子命令）
│   ├── client.py         # 浏览器客户端（频率控制 + 验证码检测）
│   ├── login.py          # 二维码登录流程
│   ├── search.py         # 搜索（多条件筛选）
│   ├── feed.py           # 帖子详情提取
│   ├── user.py           # 用户主页提取
│   ├── comment.py        # 评论（发表/回复/通知页 + 延迟 + 重试）
│   ├── interact.py       # 点赞收藏（延迟 + 频率检测 + 批次冷却）
│   ├── explore.py        # 推荐流提取
│   ├── publish.py        # 发布（图文/视频/Markdown/长文 + 延迟）
│   ├── templates.py      # 写作模板引擎
│   ├── strategy.py       # 运营策略（配额/日历/定位）
│   ├── selectors.py      # 浏览器选择器契约
│   ├── output_contracts.py # CLI JSON 输出契约
│   ├── quality.py        # 本地和 CI 质量门
│   └── sop.py            # SOP 编排引擎
└── tests/                # 单元测试
    ├── test_client.py
    ├── test_cli.py
    ├── test_search.py
    ├── test_comment.py
    ├── test_interact.py
    ├── test_publish.py
    ├── test_output_contracts.py
    ├── test_quality.py
    ├── test_selectors.py
    ├── test_templates.py
    ├── test_strategy.py
    └── test_sop.py
```

## 跨平台兼容

| 环境 | 无头模式 | 有头（扫码登录） | 备注 |
|------|----------|-----------------|------|
| Windows | OK | OK | 主力开发环境 |
| WSL2 (Win11) | OK | 用 WSLg | 需要 `playwright install-deps` |
| Linux 服务器 | OK | 不适用 | 二维码存图片文件 |

## 注意

1. **Cookie 过期**：定期会过期。`check-login` 返回 false 就重新登录。
2. **频率限制**：猛抓会出验证码。别关内置频率控制。
3. **xsec_token**：跟会话绑定的。始终用搜索结果里最新的。
4. **配额管理**：用 `strategy-check-limit` 查剩余配额，别超过。
5. **别滥用**：会封号。本工具仅供学习研究用。

---

# 融合模块

## 使用方式
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

### 使用方式

本技能主文件保留通用框架；垂直行业经验放在 `examples/` 目录，按内容类型选用：

- 先按《通用流程》跑一遍
- 再加载对应案例文件补齐行业特殊动作

当前已可用案例：

- `examples/drama-watch/case.md`（陪你看剧账号）

每个内容类型按目录组织，文件命名可为：

- `examples/<vertical>/<vertical>.md`（推荐）
- 或 `examples/<vertical>/README.md`


- `examples/lifestyle/`（待补充）
- `examples/cosmetics/`（待补充）
- `examples/fitness/`（待补充）

---

## 常用术语
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 常用术语

- `选题`：可发布、可讨论、可转发的内容切入点
- `引流钩子`：标题/开头一句用于触发停留与点击
- `结构化输出`：标题、正文、互动问句、话题、标签五元组
- `快照`：用于验证页面状态的关键证据快照
- `回放`：流程失败后重试或改道执行

## 1) 技能默认行为（所有任务都遵循）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 1) 技能默认行为（所有任务都遵循）

- **先读本技能目录下的 `persona.md`**（小红书平台专用人设/语气/发布与回复风格）。所有对外文案（发帖/评论回复/私信话术）都必须遵循。
- 开始新任务前，先读 `knowledge-base/README.md` 这个总览入口，再按 `references/xhs-knowledge-base.md` 的规则检索最近的同类记录；能复用的 pattern 不重复摸索。
- 优先输出可执行的 SOP 而非一次性内容稿
- 语言优先“能对话”而不是“写报告”：短句、口语、站位明确、可引导评论
- 所有输出默认保留“可追问点”，用于评论区继续延展

## 8) 通用提取示例（Evaluate）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 8) 通用提取示例（Evaluate）

通用字段提取脚本示例见 `references/xhs-eval-patterns.md`。

## 5) 通用发布链路（不发稿）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 5) 通用发布链路（不发稿）

详细发布执行路径请直接按 `references/xhs-publish-flows.md` 执行，避免重复维护。

发布前必须满足的核心点：

- 账号先登录创作后台，确认页面在 `openclaw` profile 可操作。
- 明确发布类型（视频 / 图文 / 长文），三要素：封面、标题、正文。
- 到达“发布”按钮可见处停手，默认不直接点击发布。
- 若涉及截图确认，优先附件形式发送到飞书，并在用户确认后再发布。

## 2.5) 账号分析（新增）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 2.5) 账号分析（新增）

按 `references/xhs-account-analysis.md` 执行。

- 默认采样最近 9-15 篇内容做轻量体检
- 从定位、内容结构、互动转化、辨识度、可持续性 5 个维度判断
- 输出必须包含“最大优势、最大短板、下一步动作”

## 3) 通用选题与对标流程
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 3) 通用选题与对标流程

## 0) 启动与环境校验（所有任务都遵循）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 0) 启动与环境校验（所有任务都遵循）

执行前先按 `references/xhs-runtime-rules.md` 中“运行规则”执行，优先遵循失败可复用顺序。

- 固定使用内置浏览器 profile：`openclaw`，出现通道异常先切回后再重试。
- 若 browser（openclaw-manager）能力处于 disabled/不可用：先执行一次轻量重试（如 status/profiles），仍不可用则进入故障引导，明确告知用户“当前浏览器工具未启用”，并引导用户按文档启用后再继续（参考：`https://docs.openclaw.ai/tools/browser`）。
- 以 `evaluate` 为先，关键节点少量 `snapshot`，单步动作最多重试一次。
- 失败后保留已获结果，切稳健路径并汇报。

## 运营成熟路径（可选）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 运营成熟路径（可选）

- 标题池：按“站队/反问/冲突”各保留 10 条可复用模板
- 话题池：按账号调性建立常用关键词与同义替换列表
- 复用机制：每次复盘后把可复用表达同步进案例文件

## 4) 通用内容模板（小红书）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 4) 通用内容模板（小红书）

每次产出至少 2 个备选：

- 标题（争议/立场/反问，≤20字优先）
- 开头钩子（1-2 句）
- 正文（3 段：观点→证据→反方）
- 互动提问（1 句）
- 话题（5-8 个）
- 风险标注（是否剧透 / 引战边界 / 版权风险）

## 实操经验（持续有效）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 实操经验（持续有效）

- **统一规则：所有浏览器操作一律走内置浏览器 profile=`openclaw`**（除非用户明确要求使用 Chrome 扩展 Relay）。
- 文字配图是稳定写入口，typed text 直接成为封面文案
- 发布话题优先用 UI 选题，不建议纯文本粘贴大量 `#话题`
- `evaluate` 批量改写富文本时，尽量少改版式，避免丢失 topic entity
- 关键步骤前保留一次快照，可用于复盘与问题定位
- `发布` 按钮可见 ≠ 发布成功；必须明确标注“到发布页停手”
- 若出现新类型评论节奏问题，优先减少每小时回复密度而非提高频率

## 3.2) 选题灵感（新增）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 3.2) 选题灵感（新增）

按 `references/xhs-topic-ideation.md` 执行。

- 将平台信号、需求信号、账号定位合并成可发布选题
- 默认输出 3-5 条，每条都要带互动钩子和三段式结构
- 产物可直接作为内容生成或 Viral Copy 的前置输入

## C. 形成选题清单（每轮至少 3 条）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

### C. 形成选题清单（每轮至少 3 条）

每条选题包含：

- 选题标题（20 字内可选）
- 观点标签（支持/反对/中性）
- 预计互动钩子
- 证据来源（哪组高互动数据）
- 风险提示（是否容易踩线）

## 6.5) 知识库沉淀（新增）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 6.5) 知识库沉淀（新增）

按 `references/xhs-knowledge-base.md` 执行。

- 总览入口固定为 `knowledge-base/README.md`
- 细分记录按类型写入 `knowledge-base/accounts/`、`knowledge-base/topics/`、`knowledge-base/patterns/`、`knowledge-base/actions/`、`knowledge-base/reviews/`
- 分析优先沉淀 `pattern` / `topic` / `review`
- 执行动作优先沉淀 `action`
- 任务结束时至少留下可检索的结论、证据、风险和下一步

## 6) 评论与回复（轻量）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 6) 评论与回复（轻量）

评论检查与回复统一遵循 `references/xhs-comment-ops.md`，并结合 `examples/reply-examples.md` 作文案风格。

- 默认优先走通知页，先对位后输入后发送。
- 默认 one-send-per-turn（如无明确要求不连发）。
- 长度、隐性承诺、风控停损点等风险控制项请以引用文件为准。

## B. 需求侧补充信号（行业/场景）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

### B. 需求侧补充信号（行业/场景）

1. 按主题去主流平台/社媒抓“评论区观点分歧”
2. 抽取支持/反对/中性观点各一组
3. 输出可发文争论点（争议但可控）

## A.1 首页推荐流分析（新增）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

### A.1 首页推荐流分析（新增）

按 `references/xhs-home-feed-analysis.md` 执行。

- 先看首页推荐流里“为什么推给你”
- 再提炼可复用的传播钩子、内容结构和选题方向
- 结果优先服务账号定位、选题灵感和后续内容判断

## 2) 账号定位（可复用）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 2) 账号定位（可复用）

每个账号先确认 4 个变量：

- 目标用户：年龄/场景/痛点（如「下班后碎片时间」「追星讨论人群」）
- 内容价值主张：每篇给用户什么（观点、情绪价值、实操建议）
- 差异化角度：同类账号不做什么、你做什么
- 风格规范：语气、长度、冲突边界（避免过激）

输出：

- 人设关键词（3-5）
- 内容支柱（3 个）
- 口头禅/固定句式（2-3 个）
- 不能碰底线（红线）清单（剧透、人身攻击、虚假承诺）

## 3.6) Viral Copy（URL → 新笔记）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 3.6) Viral Copy（URL → 新笔记）

按 `references/xhs-viral-copy-flow.md` 执行。

- 输入：目标爆款笔记 URL（可多条）。
- 输出：1 套可发布素材（封面/配图方案 + 标题 + 正文 + 话题）。
- 复刻原则：高贴合主题与结构（标题句式、封面信息层级、正文节奏、互动机制），同时避免逐字照抄与素材侵权。

## 3.5) 搜索并浏览（新增操作类型）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 3.5) 搜索并浏览（新增操作类型）

按 `references/xhs-runtime-rules.md` 的搜索与评论入口章节执行。

- 只允许从搜索结果页进入帖子；
- 优先通知/回复场景前先对位校验。
- 连续失败回退策略见引用文件。

## 7) 失败与修复（必须遵循）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 7) 失败与修复（必须遵循）

- 自动化失败先重试一次（同策略）
- 仍失败则改道：换到“更稳妥同义路径”
- 不做无效重复动作；保留当前进度可复用，报告一次用户需手动的单一动作
- 若知识库暂时不可写，先返回结构化摘要，任务结束后补记，不阻塞主流程

## A. 平台侧抓取信号（可并行）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

### A. 平台侧抓取信号（可并行）

1. 先在小红书抓同题材高互动内容（点赞/收藏/评论高于近期平均值）
2. 记录可复用字段：`title`, `hook`, `angle`, `结构标签`, `评论信号`, `互动CTA`, `标签组`
3. 汇总前 10-20 条到候选池

## 适用范围（默认即通用流程）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 适用范围（默认即通用流程）

- 账号定位与内容方向
- 选题产出与争议点挖掘
- 竞品/同类账号对标
- 小红书发布前演练与内容交付
- 发布后快速复盘（互动结构、评论回复、热点追踪）
- Viral Copy 链路（输入 URL，高贴合学习封面/配图、标题、正文并生成可发布近似结构笔记）

将每类账号的行业细节作为“案例模块（case module）”挂载到通用流程中。

## 9) 具体案例：陪你看剧（保留为特例）
> 来源: xiaohongshu-ops | 原因: 候选技能独有模块

## 9) 具体案例：陪你看剧（保留为特例）

---

# 依赖说明

本组合技能可能需要以下依赖：
- playwright
