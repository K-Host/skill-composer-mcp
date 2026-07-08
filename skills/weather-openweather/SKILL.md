---
name: weather-openweather
description: 基于 OpenWeatherMap API 的专业天气查询技能，支持丰富的气象数据维度
version: 1.0.0
author: skill-composer
tags:
  - weather
  - openweathermap
  - api
  - forecast
---

# weather-openweather

基于 OpenWeatherMap API 的专业天气查询技能，提供全面的气象数据访问能力。

## 能力：当前天气

通过 OpenWeatherMap Current Weather API 获取实时天气数据。

- 温度（支持摄氏度/华氏度切换）
- 体感温度
- 气压、湿度、云量
- 风向风速
- 紫外线指数
- 能见度

技术依赖：curl, jq

API 端点：`https://api.openweathermap.org/data/2.5/weather`

## 能力：天气预报

获取 5 天 / 3 小时间隔的详细预报。

- 逐 3 小时的温度曲线
- 天气状况描述
- 降水概率和降水量
- 风速风向变化趋势

API 端点：`https://api.openweathermap.org/data/2.5/forecast`

## 能力：空气质量

获取城市的空气质量指数（AQI）。

- PM2.5 / PM10 浓度
- NO₂、SO₂、CO、O₃ 浓度
- 空气质量等级（优/良/轻度污染/中度污染/重度污染/严重污染）

API 端点：`https://api.openweathermap.org/data/2.5/air_pollution`

## 能力：气象预警

获取官方气象预警信息。

- 预警类型（暴雨/台风/暴雪/高温等）
- 预警等级（绿/黄/橙/红）
- 预警时间范围和区域

API 端点：`https://api.openweathermap.org/data/2.5/onecall`

## 模块：历史数据

查询历史天气数据用于分析和对比。

- 过去 7 天天气回溯
- 历史同期数据对比
- 月平均气温统计

## 模块：位置管理

通过城市名或经纬度查询位置信息。

- 城市名 → 经纬度解析
- 经纬度逆解析
- 附近城市天气查询
- 收藏城市管理

API 端点：`https://api.openweathermap.org/geo/1.0/direct`

## 配置项

- `OPENWEATHER_API_KEY`：API Key（必填，从 https://openweathermap.org/api 注册）
- `OPENWEATHER_UNITS`：单位制（metric/imperial/standard，默认 metric）

## 错误处理

- API Key 无效时返回 401 错误提示
- 城市名不匹配时自动尝试相近城市
- 请求频率限制（免费版 60次/分钟）自适应降速
- 网络异常时返回上次缓存数据

## 缓存策略

- 当前天气数据缓存 5 分钟
- 预报数据缓存 15 分钟
- 位置数据缓存 7 天
- 空气质量缓存 30 分钟
