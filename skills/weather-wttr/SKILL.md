---
name: weather-wttr
description: 命令行天气查询技能，使用 wttr.in 获取全球天气信息，无需 API Key
version: 1.0.0
author: skill-composer
tags:
  - weather
  - wttr
  - curl
  - cli
---

# weather-wttr

基于 wttr.in 的命令行天气查询技能，无需注册 API Key，支持全球城市天气查询。

## 能力：实时天气查询

使用 curl 调用 wttr.in API 获取指定城市的实时天气。

- 温度、湿度、风速、能见度
- 天气状况描述（晴、多云、雨、雪等）
- 支持城市名或经纬度查询

技术依赖：curl

## 能力：天气预报

获取未来 3 天的天气预报。

- 每日最高/最低温度
- 降水概率
- 风力风向变化
- 日出日落时间

## 能力：格式化输出

支持多种输出格式。

- 简洁模式：`curl wttr.in/Beijing?format=3`
- 详细模式：`curl wttr.in/Beijing`
- JSON 模式：`curl wttr.in/Beijing?format=j1`
- PNG 图表模式：`curl wttr.in/Beijing.png`

技术依赖：jq（用于解析 JSON 输出）

## 模块：城市管理

管理常用城市列表。

- 添加/删除关注城市
- 批量查询多个城市天气
- 城市名称自动补全和模糊匹配

## 模块：天气提醒

基于天气条件触发提醒。

- 温度阈值告警（高温/低温）
- 降水提醒
- 风速告警

## 错误处理

- 城市名未找到时返回友好提示
- 网络超时自动重试（最多 2 次）
- wttr.in 服务不可用时降级到缓存数据

## 缓存策略

- 当前天气缓存 10 分钟
- 预报数据缓存 30 分钟
- 城市列表缓存 24 小时
