# ClickHouse 数据指标计算交付要求 (数据中台)

> **架构背景**：根据总体方案设计，腾讯云 MySQL 数据库定位为 **ODS 数据总线**，仅负责海量金融时间序列数据的持久化存储与写入防篡改。所有复杂的聚合分析、多表关联、以及大宽表指标计算（L2~L5）必须全面下推至内网的高性能 **ClickHouse (CK) 数据库**执行。

本文档作为数据管线重构 (E1) 阶段的输出物，定义了 MySQL 端完成数据整理后，下游 ClickHouse 如何接管复权计算与指标聚合的标准规范。

---

## 1. 基础数据同步要求 (MySQL -> ClickHouse)

ClickHouse 需要从 MySQL 同步以下两张核心原表。**严禁在 MySQL 端进行预关联计算**，必须以 Raw Data 形式同步。

### 1.1 `ods_stock_kline_daily` (原始未复权 K 线)
*   **同步策略**：增量同步 / MaterializedMySQL 引擎。
*   **CK 表引擎建议**：`ReplacingMergeTree` (使用 `trade_date`, `ts_code` 排序并去重)。
*   **特点**：保证了所有价格数据严格等于交易所原始快照，无任何复权污染。

### 1.2 `dim_stock_adjust_factor` (复权因子变动快照)
*   **同步策略**：全量/增量同步。
*   **CK 表引擎建议**：`ReplacingMergeTree`。
*   **特点**：稀疏时间序列（仅在发生分红派息的日期才有记录）。

> ⚠️ **注意**：MySQL 中的辅助连续缓存表 `ods_stock_factor_daily` **无需同步**至 CK。因为 CK 拥有更强大的时序关联引擎，可以直接在内存中实时还原连续序列。

---

## 2. 核心计算模型 1：高性能前复权视图 (CK 原生实现)

在 MySQL 中，我们不得不建立辅助表来填补非分红日的因子空白。而在 ClickHouse 中，必须利用其特有的 **`ASOF JOIN`**（或时序插值函数）来实现极速的前复权实时计算。

### 2.1 因子对齐逻辑 (ASOF JOIN)
ClickHouse 的 `ASOF JOIN` 天然适合解决“寻找左表日期之前、最接近的右表日期记录”这一金融经典问题。

**CK 视图设计参考 (`v_stock_kline_forward_adj`)**：
```sql
CREATE VIEW v_stock_kline_forward_adj AS
WITH latest_factors AS (
    -- 1. 获取每只股票当前的最新（最大）复权因子作为基准分母
    SELECT ts_code, MAX(adjust_factor) AS max_factor
    FROM dim_stock_adjust_factor
    GROUP BY ts_code
)
SELECT 
    k.ts_code,
    k.trade_date,
    -- 前复权公式：原始价格 * (当日因子 / 最新因子)
    round(k.close * f.adjust_factor / lf.max_factor, 4) AS adj_close,
    round(k.open * f.adjust_factor / lf.max_factor, 4) AS adj_open,
    round(k.high * f.adjust_factor / lf.max_factor, 4) AS adj_high,
    round(k.low * f.adjust_factor / lf.max_factor, 4) AS adj_low,
    k.pct_chg,
    k.amount
FROM ods_stock_kline_daily k
-- 2. 关键点：使用 ASOF LEFT JOIN 实现极速时序对齐，无需辅助表
ASOF LEFT JOIN dim_stock_adjust_factor f
    ON k.ts_code = f.ts_code AND k.trade_date >= f.adjust_date
-- 3. 关联最新因子计算复权
LEFT JOIN latest_factors lf 
    ON k.ts_code = lf.ts_code;
```
*   **计算优势**：完全摒弃 MySQL 复杂的关联子查询，利用 CK 内存向量化特性，即使对全市场数千万行数据进行即时复权，响应时间也能控制在几十毫秒级。

---

## 3. 核心计算模型 2：L2 行业与概念指标计算下推

目前后端的 `IndicatorService` 中包含如行业涨跌家数、领涨股等逻辑。这些聚合计算应当交由 ClickHouse 处理。

### 3.1 行业广度统计
利用 CK 的 `countIf` 特性，可以将复杂的多 `CASE WHEN` 语句极大简化。

**CK 查询参考**：
```sql
SELECT
    sw.l1_code AS industry_code,
    k.trade_date,
    countIf(k.pct_chg > 0) AS up_count,
    countIf(k.pct_chg < 0) AS down_count,
    countIf(k.pct_chg >= 9.9) AS limit_up_count,
    count() AS total_count,
    round(up_count / total_count, 4) AS internal_breadth
FROM ods_stock_kline_daily k
JOIN dim_stock_industry_sw sw ON k.ts_code = sw.code
WHERE k.trade_date = '2026-05-04'
GROUP BY sw.l1_code, k.trade_date;
```

### 3.2 行业领涨股捕获
MySQL 中使用 `GROUP_CONCAT` 强行截取字符串的方式极不优雅且性能低下。CK 提供了强大的 `argMax` 函数，专为这种“寻找组内最大值对应的其他列”而生。

**CK 查询参考 (极简高效)**：
```sql
SELECT 
    sw.l1_code AS industry_code,
    k.trade_date,
    -- 直接获取 pct_chg 最大时对应的 ts_code
    argMax(k.ts_code, k.pct_chg) AS top_stock_code,
    MAX(k.pct_chg) AS top_pct
FROM ods_stock_kline_daily k
JOIN dim_stock_industry_sw sw ON k.ts_code = sw.code
WHERE k.trade_date = '2026-05-04'
GROUP BY sw.l1_code, k.trade_date;
```

---

## 4. 交付与验收标准 (SLA)

1. **功能完整性**：CK 端必须创建 `v_stock_kline_forward_adj` 视图，保证查询该视图返回的数据与 Tushare 官方前复权接口的误差在 `±0.01`（四舍五入精度差异）以内。
2. **性能达标**：在跨度 10 年（约 2000 万行 K 线）的全市场尺度下，针对 `v_stock_kline_forward_adj` 的聚合查询（如计算全市场 MA250 穿越家数），需在 `500ms` 内返回。
3. **架构纪律性**：禁止在 CK 中修改原始 `ods_stock_kline_daily` 任何数据。所有调整、复权、降噪动作，均以 View（视图）或 Dictionary（字典）的形式隔离在计算层。
