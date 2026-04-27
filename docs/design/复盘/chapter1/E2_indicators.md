# 第 1 章 · 指标计算 SQL (E2)

## E2-S1:L1 全景指标聚合

**作为** 计算层,**我希望** 通过一段 SQL 把 ODS 层数据聚合成 L1 全景指标,**以便** 前端直接查询。

#### Task

```sql
-- ============================================
-- E2-S1-T1:L1 当日聚合(执行频率:每日 19:30 后,T 日数据齐全后执行)
-- 输入:ods_index_daily / ods_market_breadth_daily / ods_event_limit_pool / stock_kline_daily
-- 输出:ads_l1_market_overview
-- ============================================

-- 步骤 1:清理目标日数据(幂等性保证)
DELETE FROM `ads_l1_market_overview` WHERE `trade_date` = :target_date;

-- 步骤 2:插入目标日聚合
INSERT INTO `ads_l1_market_overview` (
    `trade_date`,
    `idx_sh_close`,    `idx_sh_pct`,
    `idx_sz_close`,    `idx_sz_pct`,
    `idx_cyb_close`,   `idx_cyb_pct`,
    `idx_kc50_close`,  `idx_kc50_pct`,
    `idx_bz50_close`,  `idx_bz50_pct`,
    `idx_hs300_close`, `idx_hs300_pct`,
    `idx_zz500_close`, `idx_zz500_pct`,
    `idx_zz1000_close`,`idx_zz1000_pct`,
    `idx_zz2000_close`,`idx_zz2000_pct`,
    `idx_winda_close`, `idx_winda_pct`,
    `turnover_total`, `turnover_ma5`, `turnover_ma20`, `turnover_pct_vs_ma20`, `turnover_pctile_1y`,
    `up_count`, `down_count`, `flat_count`, `up_down_ratio`,
    `limit_up_count`, `limit_down_count`, `blast_count`, `lian_count`, `max_board_height`,
    `high_60d_count`, `low_60d_count`, `market_breadth`,
    `market_regime`,
    `compute_version`
)
SELECT
    :target_date AS trade_date,

    -- ===== 核心指数(子查询) =====
    MAX(CASE WHEN ts_code = '000001.SH'  THEN close   END) AS idx_sh_close,
    MAX(CASE WHEN ts_code = '000001.SH'  THEN pct_chg END) AS idx_sh_pct,
    MAX(CASE WHEN ts_code = '399001.SZ'  THEN close   END) AS idx_sz_close,
    MAX(CASE WHEN ts_code = '399001.SZ'  THEN pct_chg END) AS idx_sz_pct,
    MAX(CASE WHEN ts_code = '399006.SZ'  THEN close   END) AS idx_cyb_close,
    MAX(CASE WHEN ts_code = '399006.SZ'  THEN pct_chg END) AS idx_cyb_pct,
    MAX(CASE WHEN ts_code = '000688.SH'  THEN close   END) AS idx_kc50_close,
    MAX(CASE WHEN ts_code = '000688.SH'  THEN pct_chg END) AS idx_kc50_pct,
    MAX(CASE WHEN ts_code = '899050.BJ'  THEN close   END) AS idx_bz50_close,
    MAX(CASE WHEN ts_code = '899050.BJ'  THEN pct_chg END) AS idx_bz50_pct,
    MAX(CASE WHEN ts_code = '000300.SH'  THEN close   END) AS idx_hs300_close,
    MAX(CASE WHEN ts_code = '000300.SH'  THEN pct_chg END) AS idx_hs300_pct,
    MAX(CASE WHEN ts_code = '000905.SH'  THEN close   END) AS idx_zz500_close,
    MAX(CASE WHEN ts_code = '000905.SH'  THEN pct_chg END) AS idx_zz500_pct,
    MAX(CASE WHEN ts_code = '000852.SH'  THEN close   END) AS idx_zz1000_close,
    MAX(CASE WHEN ts_code = '000852.SH'  THEN pct_chg END) AS idx_zz1000_pct,
    MAX(CASE WHEN ts_code = '932000.CSI' THEN close   END) AS idx_zz2000_close,
    MAX(CASE WHEN ts_code = '932000.CSI' THEN pct_chg END) AS idx_zz2000_pct,
    MAX(CASE WHEN ts_code = '8841415.WI' THEN close   END) AS idx_winda_close,  -- 实际代码以 Tushare 为准 TBD
    MAX(CASE WHEN ts_code = '8841415.WI' THEN pct_chg END) AS idx_winda_pct,

    -- ===== 成交占位(下一步 UPDATE 填充) =====
    NULL, NULL, NULL, NULL, NULL,

    -- ===== 涨跌家数占位(下一步 UPDATE 填充) =====
    NULL, NULL, NULL, NULL,
    NULL, NULL, NULL, NULL, NULL,
    NULL, NULL, NULL,

    -- ===== 市场状态占位 =====
    NULL,

    'v1' AS compute_version

FROM `ods_index_daily`
WHERE `trade_date` = :target_date
  AND `ts_code` IN (
    '000001.SH','399001.SZ','399006.SZ','000688.SH','899050.BJ',
    '000300.SH','000905.SH','000852.SH','932000.CSI','8841415.WI'
  );

-- ============================================
-- 步骤 3:UPDATE 填充成交活跃度
-- ============================================
UPDATE `ads_l1_market_overview` o
INNER JOIN (
    SELECT
        trade_date,
        SUM(amount) AS turnover_total
    FROM `stock_kline_daily`
    WHERE trade_date = :target_date
    GROUP BY trade_date
) t ON o.trade_date = t.trade_date
SET o.turnover_total = t.turnover_total
WHERE o.trade_date = :target_date;

-- 步骤 4:UPDATE 成交额均线与分位数(子查询计算近 20 / 250 日)
UPDATE `ads_l1_market_overview` o
INNER JOIN (
    SELECT
        :target_date AS trade_date,
        AVG(turnover_total) AS turnover_ma20
    FROM (
        SELECT trade_date, SUM(amount) AS turnover_total
        FROM `stock_kline_daily`
        WHERE trade_date <= :target_date
        GROUP BY trade_date
        ORDER BY trade_date DESC
        LIMIT 20
    ) t20
) m20 ON o.trade_date = m20.trade_date
SET o.turnover_ma20 = m20.turnover_ma20
WHERE o.trade_date = :target_date;

UPDATE `ads_l1_market_overview` o
INNER JOIN (
    SELECT
        :target_date AS trade_date,
        AVG(turnover_total) AS turnover_ma5
    FROM (
        SELECT trade_date, SUM(amount) AS turnover_total
        FROM `stock_kline_daily`
        WHERE trade_date <= :target_date
        GROUP BY trade_date
        ORDER BY trade_date DESC
        LIMIT 5
    ) t5
) m5 ON o.trade_date = m5.trade_date
SET o.turnover_ma5 = m5.turnover_ma5
WHERE o.trade_date = :target_date;

-- 相对 20 日均值
UPDATE `ads_l1_market_overview`
SET turnover_pct_vs_ma20 = CASE
    WHEN turnover_ma20 IS NULL OR turnover_ma20 = 0 THEN NULL
    ELSE turnover_total / turnover_ma20 - 1
END
WHERE trade_date = :target_date;

-- 1 年分位数
UPDATE `ads_l1_market_overview` o
INNER JOIN (
    SELECT
        :target_date AS trade_date,
        SUM(CASE WHEN turnover_total < (
            SELECT SUM(amount) FROM `stock_kline_daily` WHERE trade_date = :target_date
        ) THEN 1 ELSE 0 END) / COUNT(*) AS turnover_pctile_1y
    FROM (
        SELECT trade_date, SUM(amount) AS turnover_total
        FROM `stock_kline_daily`
        WHERE trade_date <= :target_date
        GROUP BY trade_date
        ORDER BY trade_date DESC
        LIMIT 250
    ) t250
) p ON o.trade_date = p.trade_date
SET o.turnover_pctile_1y = p.turnover_pctile_1y
WHERE o.trade_date = :target_date;

-- ============================================
-- 步骤 5:UPDATE 涨跌家数(从 ods_market_breadth_daily 获取)
-- ============================================
UPDATE `ads_l1_market_overview` o
INNER JOIN `ods_market_breadth_daily` b ON o.trade_date = b.trade_date
SET
    o.up_count        = b.up_count,
    o.down_count      = b.down_count,
    o.flat_count      = b.flat_count,
    o.up_down_ratio   = CASE WHEN b.down_count = 0 THEN NULL ELSE b.up_count / b.down_count END,
    o.high_60d_count  = b.high_60d_count,
    o.low_60d_count   = b.low_60d_count,
    o.market_breadth  = CASE WHEN b.total_count = 0 THEN NULL ELSE b.up_count / b.total_count END
WHERE o.trade_date = :target_date;

-- ============================================
-- 步骤 6:UPDATE 涨跌停 / 炸板 / 连板(从 ods_event_limit_pool 聚合)
-- ============================================
UPDATE `ads_l1_market_overview` o
INNER JOIN (
    SELECT
        trade_date,
        SUM(CASE WHEN pool_type = 'zt'   THEN 1 ELSE 0 END) AS limit_up_count,
        SUM(CASE WHEN pool_type = 'dt'   THEN 1 ELSE 0 END) AS limit_down_count,
        SUM(CASE WHEN pool_type = 'zb'   THEN 1 ELSE 0 END) AS blast_count,
        SUM(CASE WHEN pool_type = 'lian' THEN 1 ELSE 0 END) AS lian_count,
        MAX(CASE WHEN pool_type IN ('zt','lian') THEN board_height ELSE NULL END) AS max_board_height
    FROM `ods_event_limit_pool`
    WHERE trade_date = :target_date
    GROUP BY trade_date
) p ON o.trade_date = p.trade_date
SET
    o.limit_up_count   = p.limit_up_count,
    o.limit_down_count = p.limit_down_count,
    o.blast_count      = p.blast_count,
    o.lian_count       = p.lian_count,
    o.max_board_height = p.max_board_height
WHERE o.trade_date = :target_date;

-- ============================================
-- 步骤 7:UPDATE 市场状态分类
-- ============================================
UPDATE `ads_l1_market_overview`
SET market_regime = CASE
    -- 缩量观望:成交分位低于 20%
    WHEN turnover_pctile_1y < 0.20                       THEN 'low_vol'
    -- 普涨:涨跌比 > 3 且涨停 > 60
    WHEN up_down_ratio > 3 AND limit_up_count > 60       THEN 'broad_up'
    -- 普跌:涨跌比 < 0.33 且跌停 > 30
    WHEN up_down_ratio < 0.33 AND limit_down_count > 30  THEN 'broad_down'
    -- 否则结构分化
    ELSE 'structural'
END
WHERE trade_date = :target_date;
```

#### 关键说明

- **执行时机**:T 日 19:30 后(确保涨跌停池、涨跌家数已采集完毕)
- **幂等性**:开头 `DELETE` 保证可重跑
- **市场状态阈值**:首版用经验值,后续可基于历史分布滚动调整
- **`:target_date` 占位符**:Antigravity 实施时替换为参数化变量

#### AC

- Given 历史任意一天的数据完整,When 执行计算,Then `ads_l1_market_overview` 新增一行
- Given 同一天重复执行计算,When 执行,Then 结果一致(幂等)
- Given `market_regime` 字段,When 查询,Then 取值在 4 个枚举内

---

## E2-S2: 内存受限环境下的计算优化 (Python)

在 128MB 容器内存限制下，计算全市场广度（Market Breadth）或复权因子时，若一次性加载 5500+ 股票的 250 日复权数据，会导致 OOM (Exit Code 137)。

**优化方案**：
1. **分批迭代 (Batching)**：将全市场股票分为每 500 只一组进行处理。
2. **局部聚合**：
   - 每组独立查询数据库并计算复权/广度。
   - 计算完对应的“站上 20 日线”计数后，立即手动释放或覆盖该组 DataFrame 变量，确保内存及时回收。
3. **全局汇总**：最后将各组计数累加，计算全市场的百分比并存入 `ods_market_breadth_daily`。

**效果**：
该方案将内存占用从 300MB+ 降低至 80MB 以下，成功满足 128MB 的资源红线要求，计算耗时仅增加约 10-15 秒。
