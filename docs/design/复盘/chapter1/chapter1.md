# 第 1 章 · 市场全景看板

> **章节信息**
> - 文档版本:v1.0
> - 创建日期:2026-04-26
> - 范围:盘后体系 L1 市场全景层 + L4 情绪层(涨跌停池基础)
> - 依赖:无(本章为后续所有章节的基础)
> - 本章交付物:SQL × 5 + 字段映射 × 1 + 小程序前端 × 1 + 数据字典 × 1

---

## 背景

A 股盘后复盘的第一步是回答"今天市场是什么基调",这是后续所有结构、资金、情绪分析的锚点。本章建立**市场全景看板**所需的数据基础,从原始指数行情、涨跌停池、涨跌家数采集,到 L1 全景指标聚合,再到微信小程序前端展示,形成完整闭环。

## 目标

- 建立指数维表(`index_basic`)与日线行情(`ods_index_daily`)
- 建立涨跌停池(`ods_event_limit_pool`)与涨跌家数(`ods_market_breadth_daily`)原始数据
- 沉淀 L1 全景指标(`ads_l1_market_overview`),实现"一张表查当日基调"
- 输出微信小程序看板原型,可在 30 秒内回答"今天市场冷热"

## 详细实施步骤 (分文档)

1. **[E1: 数据库改造 (SQL)](file:///home/ubuntu/microservice-stock/docs/design/复盘/chapter1/E1_database.md)**
   - 命名重构、新建维表、ODS 表与 ADS 表结构。
2. **[E2: 指标计算 SQL](file:///home/ubuntu/microservice-stock/docs/design/复盘/chapter1/E2_indicators.md)**
   - L1 全景指标聚合逻辑、幂等性保证与市场状态分类。
3. **[E3: 微信小程序前端](file:///home/ubuntu/microservice-stock/docs/design/复盘/chapter1/E3_frontend.md)**
   - 看板首屏 WXML/WXSS 模板与数据请求逻辑。
4. **[E4: 数据字典与口径](file:///home/ubuntu/microservice-stock/docs/design/复盘/chapter1/E4_dictionary.md)**
   - 字段单位说明、数据源映射关系。
5. **[风险、规避与里程碑](file:///home/ubuntu/microservice-stock/docs/design/复盘/chapter1/Risk_Milestones.md)**
   - 避坑指南、采集性能限制与 Day 1-14 实施里程碑。

---

## 核心指标看板效果图 (预览)

(此处可由 Antigravity 生成看板 Mockup 图片)

## 确认与下一步

如果以上内容你审核通过,Antigravity 可以直接拿去实施。

确认后我们进入 **第 2 章 · 行业与风格分化**。