---
name: research-skill
description: 学术研究技能，支持文献检索、分析和综述撰写
version: 2.1.0
author: research-team
tags:
  - research
  - academic
  - literature
---

# research-skill

学术研究辅助技能，帮助用户进行文献检索、分析和综述撰写。

## 能力：文献检索

使用 Google Scholar API 和 Semantic Scholar 进行文献搜索。

- 支持关键词搜索和引用搜索
- 自动提取标题、作者、摘要、引用数
- 支持按年份、领域过滤

技术依赖：requests, beautifulsoup4

## 能力：文献分析

对检索到的文献进行深度分析。

- 提取关键发现和方法论
- 识别研究趋势
- 生成文献对比表格

技术依赖：pandas, numpy

## 模块：综述撰写

基于分析结果撰写文献综述。

- 自动生成综述大纲
- 按主题组织内容
- 生成参考文献列表（APA/MLA/Chicago格式）

## 模块：引用管理

管理和格式化引用。

- 支持 BibTeX 导入导出
- 自动生成引用格式
- 去重和冲突检测

## 错误处理

当 API 调用失败时自动重试（最多3次），指数退避策略。

## 缓存策略

检索结果缓存 60 分钟，减少重复 API 调用。
