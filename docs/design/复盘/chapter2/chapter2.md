# 第 2 章 · 行业与风格分化

> **章节信息**
> - 文档版本: v1.1
> - 更新日期: 2026-04-26
> - 范围: 盘后体系 L2 结构分化层
> - 交付物: SQL × 6 + 采集逻辑 × 2 + API 契约 × 1

---

## 背景

在回答完“今天市场是什么基调”后，下一个核心问题是“今天市场在交易什么主线”。本章建立**行业与风格分化看板**，通过申万行业、风格因子、概念板块三个维度，为后续的个股异动分析和行业归因提供数据基础。

## 目标

- 建立申万行业指数与概念板块的日线行情 ODS 层。
- 沉淀 L2 行业、概念及风格因子的 ADS 衍生指标。
- 提供标准化的 API 接口契约，供前端展示行业热力图、风格卡片和概念榜单。

## 详细实施步骤 (分文档)

1. **[E1: 数据库改造 (SQL)](file:///home/ubuntu/microservice-stock/docs/design/复盘/chapter2/E1_database.md)**
   - 申万行业、概念板块、风格因子的 ODS/ADS/DIM 表结构定义。
2. **[E2: 指标计算 SQL](file:///home/ubuntu/microservice-stock/docs/design/复盘/chapter2/E2_indicators.md)**
   - 行业内部广度、排名动量、概念持续性及风格差值计算逻辑。
3. **[E3: API 接口契约](file:///home/ubuntu/microservice-stock/docs/design/复盘/chapter2/E3_api_contract.md)**
   - 定义前端所需的 JSON 返回结构（行业 Top/Bottom、风格 VS、概念榜单）。
4. **[E4: 数据字典与口径](file:///home/ubuntu/microservice-stock/docs/design/复盘/chapter2/E4_dictionary.md)**
   - 字段单位说明、akshare 数据源映射映射规则。
5. **[E5: 数据采集策略](file:///home/ubuntu/microservice-stock/docs/design/复盘/chapter2/E5_acquisition_strategy.md)**
   - 针对 akshare 申万改版与同花顺频率限制的采集优化方案。
6. **[风险与里程碑](file:///home/ubuntu/microservice-stock/docs/design/复盘/chapter2/Risk_Milestones.md)**
   - 避坑指南、MySQL 5.7 窗口函数模拟方案及实施周期。

---

## 确认与下一步

本章专注于**后端逻辑与数据基础**。完成后，第 5 章（个股异动池）可以直接 JOIN `ads_l2_industry_daily` 为个股打上精准的行业和风格标签。

确认执行后，请按里程碑计划开始 D1-D3 的数据库建表工作。
