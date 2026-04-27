# 第 2 章 · 指标计算 SQL (E2)

## E2-S1: L2 行业指标聚合

**输入**: `ods_sw_index_daily` / `stock_kline_daily` / `stock_industry_sw`
**输出**: `ads_l2_industry_daily`
**时机**: T 日 19:30 后

```sql
-- ============================================
-- E2-S1-T1: L2 行业指标当日聚合
-- ============================================

DELETE FROM `ads_l2_industry_daily` WHERE `trade_date` = :target_date;

-- 1. 基础行情插入
INSERT INTO `ads_l2_industry_daily` (
    trade_date, industry_code, industry_name,
    close, pct_chg, amount, turnover_rate,
    pe_ttm, pb, dv_ratio, compute_version
)
SELECT
    trade_date, ts_code, name,
    close, pct_chg, amount, turnover_rate,
    pe_ttm, pb, dv_ratio, 'v1'
FROM `ods_sw_index_daily`
WHERE `trade_date` = :target_date AND `level` = 'l1';

-- 2. 内部广度计算 (JOIN 个股 K 线与行业映射)
UPDATE `ads_l2_industry_daily` o
INNER JOIN (
    SELECT
        sw.l1_code AS industry_code,
        SUM(CASE WHEN k.pct_chg > 0  THEN 1 ELSE 0 END) AS up_count,
        SUM(CASE WHEN k.pct_chg < 0  THEN 1 ELSE 0 END) AS down_count,
        SUM(CASE WHEN k.pct_chg >= 0.099 THEN 1 ELSE 0 END) AS limit_up_count,
        COUNT(*) AS total_count
    FROM `stock_kline_daily` k
    INNER JOIN `stock_industry_sw` sw ON k.code = sw.code
    WHERE k.trade_date = :target_date AND k.trade_status = 1
    GROUP BY sw.l1_code
) b ON o.industry_code = b.industry_code
SET
    o.up_count         = b.up_count,
    o.down_count       = b.down_count,
    o.limit_up_count   = b.limit_up_count,
    o.total_count      = b.total_count,
    o.internal_breadth = b.up_count / b.total_count;

-- 3. 领涨股计算 (每个行业涨幅第一的股票)
UPDATE `ads_l2_industry_daily` o
INNER JOIN (
    SELECT 
        sw.l1_code AS industry_code,
        SUBSTRING_INDEX(GROUP_CONCAT(k.code ORDER BY k.pct_chg DESC), ',', 1) AS top_code,
        MAX(k.pct_chg) AS top_pct
    FROM `stock_kline_daily` k
    INNER JOIN `stock_industry_sw` sw ON k.code = sw.code
    WHERE k.trade_date = :target_date AND k.trade_status = 1
    GROUP BY sw.l1_code
) t ON o.industry_code = t.industry_code
INNER JOIN `stock_basic_info` sb ON t.top_code = sb.ts_code
SET 
    o.top_stock_code = t.top_code,
    o.top_stock_name = sb.name,
    o.top_stock_pct  = t.top_pct
WHERE o.trade_date = :target_date;

-- 4. 排名计算 (MySQL 5.7 变量方案)
UPDATE `ads_l2_industry_daily` o
INNER JOIN (
    SELECT industry_code, @rk := @rk + 1 AS rk
    FROM (SELECT industry_code FROM `ads_l2_industry_daily` 
          WHERE trade_date = :target_date ORDER BY pct_chg DESC) t,
         (SELECT @rk := 0) v
) r ON o.industry_code = r.industry_code
SET o.rank_today = r.rk
WHERE o.trade_date = :target_date;

-- 5. 5日排名变化 (今日排名 - 5日前排名)
UPDATE `ads_l2_industry_daily` o
INNER JOIN (
    SELECT industry_code, rank_today AS rank_5d_ago
    FROM `ads_l2_industry_daily`
    WHERE trade_date = (
        SELECT MAX(cal_date) FROM `trade_cal` 
        WHERE cal_date <= DATE_SUB(:target_date, INTERVAL 5 DAY) AND is_open = 1
    )
) r5 ON o.industry_code = r5.industry_code
SET o.rank_diff_5d = o.rank_today - r5.rank_5d_ago
WHERE o.trade_date = :target_date;

-- 6. 估值分位数 (近 5 年历史对比)
-- 注意: 该步骤在历史补全后执行, 计算较为耗时
UPDATE `ads_l2_industry_daily` o
INNER JOIN (
    SELECT 
        a.industry_code,
        SUM(CASE WHEN h.pe_ttm < a.pe_ttm THEN 1 ELSE 0 END) / COUNT(*) AS pe_pctile
    FROM `ads_l2_industry_daily` a
    INNER JOIN `ads_l2_industry_daily` h ON a.industry_code = h.industry_code
    WHERE a.trade_date = :target_date 
      AND h.trade_date BETWEEN DATE_SUB(:target_date, INTERVAL 5 YEAR) AND :target_date
      AND h.pe_ttm IS NOT NULL
    GROUP BY a.industry_code
) p ON o.industry_code = p.industry_code
SET o.pe_pctile_5y = p.pe_pctile
WHERE o.trade_date = :target_date;

```

---

## E2-S2: L2 概念指标聚合

**输入**: `ods_concept_kline_daily` / `stock_sector_cons_ths`
**输出**: `ads_l2_concept_daily`

```sql
-- ============================================
-- E2-S2-T1: L2 概念指标当日聚合
-- ============================================

DELETE FROM `ads_l2_concept_daily` WHERE `trade_date` = :target_date;

-- 1. 基础行情插入
INSERT INTO `ads_l2_concept_daily` (
    trade_date, concept_code, concept_name,
    pct_chg, amount, turnover_rate,
    up_count, down_count, constituent_count, compute_version
)
SELECT
    trade_date, concept_code, concept_name,
    pct_chg, amount, turnover_rate,
    up_count, down_count, constituent_count, 'v1'
FROM `ods_concept_kline_daily`
WHERE `trade_date` = :target_date;

-- 2. 持续性评分逻辑 (简化版)
-- 规则: 今日 Top10 且昨日也在 Top10 的赋予高分
UPDATE `ads_l2_concept_daily` c
INNER JOIN (
    SELECT concept_code, rank_today FROM `ads_l2_concept_daily`
    WHERE trade_date = (SELECT MAX(cal_date) FROM `trade_cal` WHERE cal_date < :target_date AND is_open = 1)
) y ON c.concept_code = y.concept_code
SET c.persistence_score = CASE
    WHEN c.rank_today <= 10 AND y.rank_today <= 10 THEN 0.9
    WHEN c.rank_today <= 10 AND y.rank_today <= 30 THEN 0.6
    WHEN c.rank_today <= 10 THEN 0.3
    ELSE 0.1 END
WHERE c.trade_date = :target_date;
```

---

## E2-S3: L2 风格因子计算

**核心逻辑**: 计算多头指数与空头指数的收益差。

```sql
-- ============================================
-- E2-S3-T1: 风格因子计算
-- ============================================

INSERT INTO `ads_l2_style_factor` (
    trade_date, factor_code, factor_name,
    long_pct, short_pct, spread_today, direction, compute_version
)
SELECT
    :target_date, f.factor_code, f.factor_name,
    l.pct_chg, s.pct_chg,
    l.pct_chg - s.pct_chg,
    CASE WHEN (l.pct_chg - s.pct_chg) > 0.005 THEN 'long_dominant'
         WHEN (l.pct_chg - s.pct_chg) < -0.005 THEN 'short_dominant'
         ELSE 'balanced' END,
    'v1'
FROM `dim_style_factor` f
INNER JOIN `ods_index_daily` l ON f.long_index = l.ts_code AND l.trade_date = :target_date
INNER JOIN `ods_index_daily` s ON f.short_index = s.ts_code AND s.trade_date = :target_date
WHERE f.is_active = 1;
```
