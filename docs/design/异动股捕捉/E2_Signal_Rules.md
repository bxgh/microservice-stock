# E2 · 信号判定规则

### E2-S1 L8 强异动复用

L8 已实现的 6 类信号(`top_gainer / top_loser / high_turnover / volume_spike / breakout / lhb`)直接同步到统一池。

#### E2-S1-T1 同步 SQL

```sql
-- 文件: sql/anomaly/01_sync_strong.sql
-- 执行时机: 每日 17:20,在 L8 ETL 之后
-- 输入: ads_l8_stock_anomaly (L8 已存在)
-- 输出: ads_l8_unified_signal (pool_type='strong')

INSERT INTO ads_l8_unified_signal (
    trade_date, ts_code, name, industry_sw1, industry_sw3,
    pool_type, signal_type, signal_subtype,
    pct_chg, turnover_rate, volume_ratio_5d, amount, main_net_inflow,
    signal_features, raw_score, compute_version
)
SELECT
    a.trade_date,
    a.ts_code,
    a.name,
    a.industry_sw1,
    b.industry_sw3,
    'strong'                              AS pool_type,
    a.anomaly_type                        AS signal_type,
    NULL                                  AS signal_subtype,
    a.pct_chg,
    a.turnover_rate,
    k.volume_ratio_5d,
    a.amount,
    a.main_net_inflow,
    JSON_OBJECT(
        'board_height',   IFNULL(a.board_height, 0),
        'lhb_yz_buy',     IFNULL(a.lhb_net_buy_score, 0),
        'has_event',      EXISTS(SELECT 1 FROM ads_l6_event_daily e
                                 WHERE e.trade_date = a.trade_date AND e.ts_code = a.ts_code)
    )                                     AS signal_features,
    a.attention_score                     AS raw_score,
    'v20260502'                           AS compute_version
FROM ads_l8_stock_anomaly a
LEFT JOIN stock_basic_info b ON a.ts_code = b.ts_code
LEFT JOIN (
    SELECT ts_code, trade_date,
           AVG(vol / NULLIF(avg_vol_20d, 0)) AS volume_ratio_5d
    FROM stock_kline_daily
    WHERE trade_date BETWEEN DATE_SUB(@td, INTERVAL 7 DAY) AND @td
    GROUP BY ts_code, trade_date
) k ON k.ts_code = a.ts_code AND k.trade_date = a.trade_date
WHERE a.trade_date = @td;
```

#### E2-S1-T1-AC 验收标准

> **Given** L8 当日产出 50 行异动  
> **When** 执行 E2-S1-T1  
> **Then** `ads_l8_unified_signal` 当日 `pool_type='strong'` 行数 = 50,且每行 `signal_features` 非空

---

### E2-S2 L8.5 启动前异动判定

#### E2-S2-T1 组合 1 龙头预备役 ⭐ 第一优先级

**判定五要素**(全部满足):

| # | 条件 | 阈值 | 数据源 |
|---|---|---|---|
| 1 | 主力资金排名跃升 | T-5 至 T-1 排名均值 > 100,T 日排名 ≤ 50 | `ods_moneyflow_stock` |
| 2 | 行业内涨幅分位上升 | T-5 至 T-1 均值 > 0.50,T 日 ≤ 0.20 | `stock_kline_daily` + `stock_industry_sw` |
| 3 | 量能温和放大 | 5 日量比均值 ∈ [1.5, 2.5] | `stock_kline_daily` |
| 4 | 无公告催化 | 当日及前 3 日 `ads_l6_event_daily` 无记录 | `ads_l6_event_daily` |
| 5 | 板块整体强势 | 所属申万一级 5 日涨幅在全市场前 30% | `ads_l2_industry_daily` |

##### E2-S2-T1.1 主力资金排名跃升临时表

```sql
-- 文件: sql/anomaly/02_combo1_capital_rank.sql

DROP TEMPORARY TABLE IF EXISTS tmp_capital_rank_jump;
CREATE TEMPORARY TABLE tmp_capital_rank_jump (
    ts_code      VARCHAR(20) PRIMARY KEY,
    rank_today   INT,
    rank_avg_5d  DECIMAL(8,2)
) ENGINE=Memory;

-- 当日排名(按主力净流入降序)
INSERT INTO tmp_capital_rank_jump (ts_code, rank_today)
SELECT ts_code, @rk := @rk + 1 AS rank_today
FROM ods_moneyflow_stock,
     (SELECT @rk := 0) v
WHERE trade_date = @td
ORDER BY net_mf_amount DESC;

-- 前 5 日均排名
UPDATE tmp_capital_rank_jump t
JOIN (
    SELECT ts_code, AVG(rk) AS rank_avg_5d
    FROM (
        SELECT trade_date, ts_code,
               IF(@d2 = trade_date, @rk2 := @rk2 + 1, @rk2 := 1) AS rk,
               @d2 := trade_date AS dummy
        FROM ods_moneyflow_stock,
             (SELECT @rk2 := 0, @d2 := NULL) v
        WHERE trade_date BETWEEN DATE_SUB(@td, INTERVAL 7 DAY) AND DATE_SUB(@td, INTERVAL 1 DAY)
        ORDER BY trade_date, net_mf_amount DESC
    ) ranked
    GROUP BY ts_code
) avg5 ON avg5.ts_code = t.ts_code
SET t.rank_avg_5d = avg5.rank_avg_5d;
```

> **MySQL 5.7 注意**:无窗口函数,排名用变量法。变量赋值依赖 ORDER BY 在子查询中生效,**生产环境建议在 Python 侧用 pandas 排名后写回临时表**,SQL 可读性更高、不易出错。

##### E2-S2-T1.2 行业内涨幅分位临时表

```sql
DROP TEMPORARY TABLE IF EXISTS tmp_industry_rank_jump;
CREATE TEMPORARY TABLE tmp_industry_rank_jump (
    ts_code              VARCHAR(20) PRIMARY KEY,
    rank_pct_today       DECIMAL(6,4)  COMMENT '当日行业内分位',
    rank_pct_avg_5d      DECIMAL(6,4)  COMMENT '前 5 日均分位'
) ENGINE=Memory;

-- 实施建议:此处 SQL 复杂度高,推荐用 Python pandas 计算
-- 算法: 对每日按 industry_sw1 分组,计算每只股 pct_chg 在组内的分位
-- 然后取 T 日分位 vs T-5 至 T-1 均值
```

##### E2-S2-T1.3 量比一致性临时表

```sql
DROP TEMPORARY TABLE IF EXISTS tmp_vol_consistency;
CREATE TEMPORARY TABLE tmp_vol_consistency (
    ts_code              VARCHAR(20) PRIMARY KEY,
    consistency_days     TINYINT      COMMENT '连续满足量比 ∈ [1.5,2.5] 的天数'
) ENGINE=Memory;

INSERT INTO tmp_vol_consistency (ts_code, consistency_days)
SELECT
    ts_code,
    SUM(CASE WHEN volume_ratio_daily BETWEEN 1.5 AND 2.5 THEN 1 ELSE 0 END) AS consistency_days
FROM (
    SELECT
        ts_code, trade_date,
        vol / NULLIF(avg_vol_20d, 0) AS volume_ratio_daily
    FROM stock_kline_daily
    WHERE trade_date BETWEEN DATE_SUB(@td, INTERVAL 4 DAY) AND @td
) t
GROUP BY ts_code
HAVING consistency_days >= 3;
```

##### E2-S2-T1.4 板块强势临时表

```sql
DROP TEMPORARY TABLE IF EXISTS tmp_sector_strength;
CREATE TEMPORARY TABLE tmp_sector_strength (
    industry_sw1            VARCHAR(50) PRIMARY KEY,
    sector_5d_pct_chg       DECIMAL(10,6),
    sector_5d_rank_pct      DECIMAL(6,4)  COMMENT '5 日涨幅在全行业内的分位(0=最强)'
) ENGINE=Memory;

INSERT INTO tmp_sector_strength
SELECT
    industry_sw1,
    sector_5d_pct_chg,
    (@rk_sec := @rk_sec + 1) / total.cnt AS sector_5d_rank_pct
FROM (
    SELECT
        industry_sw1,
        SUM(pct_chg) AS sector_5d_pct_chg
    FROM ads_l2_industry_daily
    WHERE trade_date BETWEEN DATE_SUB(@td, INTERVAL 4 DAY) AND @td
    GROUP BY industry_sw1
) sec,
(SELECT @rk_sec := 0) v,
(SELECT COUNT(DISTINCT industry_sw1) AS cnt FROM ads_l2_industry_daily WHERE trade_date = @td) total
ORDER BY sec.sector_5d_pct_chg DESC;
```

##### E2-S2-T1.5 组合 1 主判定 SQL

```sql
INSERT INTO ads_l8_unified_signal (
    trade_date, ts_code, name, industry_sw1, industry_sw3,
    pool_type, signal_type, signal_subtype,
    pct_chg, turnover_rate, volume_ratio_5d, amount, main_net_inflow,
    signal_features, raw_score, compute_version
)
SELECT
    @td,
    s.ts_code,
    s.name,
    s.industry_sw1,
    s.industry_sw3,
    'early',
    'early_combo_1',
    'leader_candidate',
    k.pct_chg,
    k.turnover_rate,
    k_avg.volume_ratio_5d,
    k.amount,
    mf.net_mf_amount,
    JSON_OBJECT(
        'rank_jump_capital',
            JSON_OBJECT('from', mr.rank_avg_5d, 'to', mr.rank_today),
        'rank_jump_industry',
            JSON_OBJECT('from', ir.rank_pct_avg_5d, 'to', ir.rank_pct_today),
        'vol_consistency_days', vc.consistency_days,
        'has_announcement',     0,
        'sector_5d_rank_pct',   sr.sector_5d_rank_pct
    ),
    -- raw_score 计算见 E3-S2-T1
    LEAST(100, GREATEST(0,
          (100 - LEAST(mr.rank_today, 100)) * 0.30
        + (1 - ir.rank_pct_today) * 100 * 0.25
        + (k_avg.volume_ratio_5d - 1.0) * 50 * 0.20
        + (1 - sr.sector_5d_rank_pct) * 100 * 0.15
        + 10
    )),
    'v20260502'
FROM stock_basic_info s
JOIN stock_kline_daily k        ON k.ts_code = s.ts_code AND k.trade_date = @td
JOIN (
    SELECT ts_code, AVG(vol / NULLIF(avg_vol_20d, 0)) AS volume_ratio_5d
    FROM stock_kline_daily
    WHERE trade_date BETWEEN DATE_SUB(@td, INTERVAL 4 DAY) AND @td
    GROUP BY ts_code
) k_avg                         ON k_avg.ts_code = s.ts_code
JOIN tmp_capital_rank_jump mr   ON mr.ts_code = s.ts_code
JOIN tmp_industry_rank_jump ir  ON ir.ts_code = s.ts_code
JOIN tmp_vol_consistency vc     ON vc.ts_code = s.ts_code
JOIN tmp_sector_strength sr     ON sr.industry_sw1 = s.industry_sw1
LEFT JOIN ads_l6_event_daily e  ON e.ts_code = s.ts_code
                                AND e.trade_date BETWEEN DATE_SUB(@td, INTERVAL 3 DAY) AND @td
LEFT JOIN ods_moneyflow_stock mf ON mf.ts_code = s.ts_code AND mf.trade_date = @td
WHERE
    s.list_status = 'L'
    AND s.name NOT LIKE '%ST%'
    AND DATEDIFF(@td, s.list_date) > 60
    AND e.ts_code IS NULL
    -- 五要素
    AND mr.rank_avg_5d > 100 AND mr.rank_today <= 50
    AND ir.rank_pct_avg_5d > 0.50 AND ir.rank_pct_today <= 0.20
    AND k_avg.volume_ratio_5d BETWEEN 1.5 AND 2.5
    AND vc.consistency_days >= 3
    AND sr.sector_5d_rank_pct <= 0.30;
```

##### E2-S2-T1.5-AC 验收标准

> **Given** 当日全市场行情已入库,L2/L3/L6 已 ETL 完成  
> **When** 执行组合 1 判定  
> **Then** 产出条数 ∈ [0, 30](正常市场环境;异常市况可能超出),且每条 `signal_features.rank_jump_capital.from > 100 AND .to <= 50`

---

#### E2-S2-T2 组合 3 连板接力候选 ⭐ 第二优先级

**判定四要素**:

| # | 条件 | 阈值 |
|---|---|---|
| 1 | 所属板块当日有 1-2 只首板涨停 | 申万一级行业,首板数 ∈ [1, 2] |
| 2 | 板块过去 5 日涨幅在行业前 30% | 见 E2-S2-T1.4 |
| 3 | 自身振幅 > 5% 但未封板 | `(high - low) / pre_close > 0.05` 且 `pct_chg < 0.099`(主板) |
| 4 | 主力资金当日净流入 | `main_net_inflow > 0` |

```sql
-- 文件: sql/anomaly/04_combo3_relay.sql

-- 步骤 1: 找出当日有首板的行业(1-2 只)
DROP TEMPORARY TABLE IF EXISTS tmp_firstboard_sectors;
CREATE TEMPORARY TABLE tmp_firstboard_sectors AS
SELECT industry_sw1, COUNT(*) AS firstboard_cnt
FROM ads_l8_stock_anomaly
WHERE trade_date = @td
  AND anomaly_type = 'top_gainer'
  AND board_height = 1
GROUP BY industry_sw1
HAVING firstboard_cnt BETWEEN 1 AND 2;

-- 步骤 2: 主判定
INSERT INTO ads_l8_unified_signal (...)
SELECT
    @td, s.ts_code, s.name, s.industry_sw1, s.industry_sw3,
    'early', 'early_combo_3', 'relay_candidate',
    k.pct_chg, k.turnover_rate, k_avg.volume_ratio_5d, k.amount, mf.net_mf_amount,
    JSON_OBJECT(
        'sector_firstboard_count', fs.firstboard_cnt,
        'amplitude',               (k.high - k.low) / k.pre_close,
        'sector_5d_rank_pct',      sr.sector_5d_rank_pct,
        'main_net_inflow',         mf.net_mf_amount
    ),
    LEAST(100, GREATEST(0,
          ((k.high - k.low) / k.pre_close) * 100 * 0.30
        + (1 - sr.sector_5d_rank_pct) * 100 * 0.30
        + LEAST(50, mf.net_mf_amount / 10000000) * 0.25
        + (CASE WHEN fs.firstboard_cnt = 1 THEN 100 ELSE 70 END) * 0.15
    )),
    'v20260502'
FROM stock_basic_info s
JOIN tmp_firstboard_sectors fs ON fs.industry_sw1 = s.industry_sw1
JOIN tmp_sector_strength sr    ON sr.industry_sw1 = s.industry_sw1
JOIN stock_kline_daily k       ON k.ts_code = s.ts_code AND k.trade_date = @td
JOIN ods_moneyflow_stock mf    ON mf.ts_code = s.ts_code AND mf.trade_date = @td
JOIN (
    SELECT ts_code, AVG(vol / NULLIF(avg_vol_20d, 0)) AS volume_ratio_5d
    FROM stock_kline_daily
    WHERE trade_date BETWEEN DATE_SUB(@td, INTERVAL 4 DAY) AND @td
    GROUP BY ts_code
) k_avg ON k_avg.ts_code = s.ts_code
WHERE
    s.list_status = 'L'
    AND s.name NOT LIKE '%ST%'
    AND DATEDIFF(@td, s.list_date) > 60
    -- 排除已涨停的(它就是首板,不是接力候选)
    AND k.pct_chg < 0.095
    -- 振幅 > 5%
    AND (k.high - k.low) / k.pre_close > 0.05
    AND mf.net_mf_amount > 0
    AND sr.sector_5d_rank_pct <= 0.30;
```

##### E2-S2-T2-AC 验收标准

> **Given** 当日有 3 个行业各有 1-2 只首板涨停  
> **When** 执行组合 3 判定  
> **Then** 产出的所有候选股,其 `industry_sw1` 都在这 3 个行业内,且 `pct_chg < 0.095`

---

#### E2-S2-T3 组合 2 箱体突破前蓄势 ⭐ 第三优先级

**判定四要素**:

| # | 条件 | 阈值 |
|---|---|---|
| 1 | 60 日内多次测试同一压力位 | `MAX(close, 60d)` ±2% 区间内,触及次数 ≥ 3 |
| 2 | 均线粘合 | 5/10/20 日 MA 相对乖离率 < 历史 10% 分位 |
| 3 | 换手率渐进式抬升 | 5 日均换手 / 20 日均换手 > 1.2 |
| 4 | 板块强势 | 同 E2-S2-T1.4 |

> **实施建议**:此组合的"压力位测试次数"和"均线乖离率分位"用 SQL 写非常复杂,**强烈推荐 Python 实现**。Antigravity 可参考以下 pandas 伪代码:

```python
# 文件: scripts/anomaly/combo2.py
# 在项目根目录执行: python -m scripts.anomaly.combo2 --date 2026-05-02

import pandas as pd
from app.utils.db import get_engine

def detect_combo2(trade_date: str) -> pd.DataFrame:
    """箱体突破前蓄势检测"""
    eng = get_engine()
    
    # 1. 取近 60 日 K 线
    sql = """
    SELECT ts_code, trade_date, close, high, low, vol, turnover_rate
    FROM stock_kline_daily
    WHERE trade_date BETWEEN DATE_SUB(:td, INTERVAL 60 DAY) AND :td
    """
    df = pd.read_sql(sql, eng, params={'td': trade_date})
    
    candidates = []
    for ts_code, g in df.groupby('ts_code'):
        g = g.sort_values('trade_date')
        if len(g) < 60:
            continue
        
        # 条件 1: 压力位测试次数
        resistance = g['high'].max()
        touches = ((g['high'] >= resistance * 0.98) & (g['high'] <= resistance * 1.02)).sum()
        if touches < 3:
            continue
        
        # 条件 2: 均线粘合(乖离率分位)
        ma5  = g['close'].rolling(5).mean().iloc[-1]
        ma10 = g['close'].rolling(10).mean().iloc[-1]
        ma20 = g['close'].rolling(20).mean().iloc[-1]
        deviation_today = (max(ma5, ma10, ma20) - min(ma5, ma10, ma20)) / ma20
        # 与历史 60 日乖离率分布对比
        # ...省略,见完整脚本
        
        # 条件 3: 换手率抬升
        tor_5d  = g['turnover_rate'].tail(5).mean()
        tor_20d = g['turnover_rate'].tail(20).mean()
        if tor_5d / tor_20d <= 1.2:
            continue
        
        candidates.append({
            'ts_code': ts_code,
            'resistance_level': resistance,
            'box_test_count': touches,
            'ma_convergence': deviation_today,
            'turnover_acceleration': tor_5d / tor_20d
        })
    
    return pd.DataFrame(candidates)
```

##### E2-S2-T3-AC 验收标准

> **Given** Python 脚本运行完成  
> **When** 查询 `signal_type='early_combo_2'`  
> **Then** 每条记录的 `signal_features.box_test_count >= 3` 且 `signal_features.turnover_acceleration > 1.2`

---

#### E2-S2-T4 组合 4 趋势反转早期 ⭐ 第四优先级

**判定四要素**(**两阶段判定**):

| # | 条件 | 阈值 | 阶段 |
|---|---|---|---|
| 1 | 首次站稳 250 日线 | 跌破 250 日线 > 60 日,T 日首次 close > MA250 | T 日 |
| 2 | 站稳后回踩 5/10 日线不破 | T+1 至 T+5 期间 low > MA10 | T+1 ~ T+5 |
| 3 | 回踩缩量 | 回踩日量比 < 1.0 | T+1 ~ T+5 |
| 4 | 板块估值低分位 | L5 行业 PE-TTM 分位 < 0.30 | T 日 |

##### E2-S2-T4.1 候选追踪表(跨日跟踪)

```sql
CREATE TABLE `tmp_combo4_candidates` (
    `ts_code`           VARCHAR(20) NOT NULL,
    `t0_date`           DATE        NOT NULL  COMMENT '首次站稳 MA250 日',
    `ma250_at_t0`       DECIMAL(16,4),
    `close_at_t0`       DECIMAL(16,4),
    `industry_sw1`      VARCHAR(50),
    `pe_ttm_pctile_t0`  DECIMAL(6,4)          COMMENT '行业 PE-TTM 分位',
    `verified`          TINYINT(1)  DEFAULT 0 COMMENT '是否已 T+5 验证',
    `verify_date`       DATE,
    `created_at`        TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`ts_code`, `t0_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='组合 4 跨日候选追踪';
```

##### E2-S2-T4.2 Python 调度逻辑

```python
# 文件: scripts/anomaly/combo4.py

def daily_run(trade_date: str):
    # 步骤 1: T 日筛选首次站稳 MA250 的股票,加入候选表
    add_new_candidates(trade_date)
    
    # 步骤 2: 检查 T-5 候选是否完成验证(T+5 已到)
    verify_candidates(trade_date, lookback_days=5)
    
    # 步骤 3: 已验证通过的写入 ads_l8_unified_signal
    promote_verified_to_signal(trade_date)
```

##### E2-S2-T4-AC 验收标准

> **Given** 5 个交易日前有 10 只股进入组合 4 候选池  
> **When** T+5 验证执行后  
> **Then** 候选表中 `verified=1` 行数 ∈ [0, 10],通过验证的写入 `ads_l8_unified_signal` 当日 `signal_type='early_combo_4'`

---

### E2-S3 L8.6 陷阱信号判定

#### E2-S3-T1 诱多放量

```yaml
判定:
  - T-1 至 T 日量比 > 2.0
  - T-1 至 T 日 close 创 5 日新高
  - T+1 收盘价跌破 T-1 收盘价
判定时机: T+1 收盘后(滞后 1 日)
signal_type: trap_lure_volume
```

```sql
-- 文件: sql/anomaly/05_trap_lure_volume.sql

INSERT INTO ads_l8_unified_signal (...)
SELECT
    @td, k0.ts_code, s.name, s.industry_sw1, s.industry_sw3,
    'trap', 'trap_lure_volume', NULL,
    k0.pct_chg, k0.turnover_rate,
    k0.vol / NULLIF(k0.avg_vol_20d, 0),
    k0.amount, mf.net_mf_amount,
    JSON_OBJECT(
        'trap_subtype',     'lure_volume',
        'lure_high_close',  km1.close,
        'today_close',      k0.close,
        'drop_pct',         (k0.close - km1.close) / km1.close,
        'lure_vol_ratio',   km1.vol / NULLIF(km1.avg_vol_20d, 0)
    ),
    LEAST(100, GREATEST(0, ABS((k0.close - km1.close) / km1.close) * 1500)),
    'v20260502'
FROM stock_kline_daily k0
JOIN stock_kline_daily km1 ON km1.ts_code = k0.ts_code
                           AND km1.trade_date = DATE_SUB(@td, INTERVAL 1 DAY)
JOIN stock_basic_info s    ON s.ts_code = k0.ts_code
LEFT JOIN ods_moneyflow_stock mf ON mf.ts_code = k0.ts_code AND mf.trade_date = @td
WHERE
    k0.trade_date = @td
    AND km1.vol / NULLIF(km1.avg_vol_20d, 0) > 2.0
    -- T-1 创 5 日新高(简化:取 T-6 至 T-2 最高 close)
    AND km1.close = (
        SELECT MAX(close) FROM stock_kline_daily
        WHERE ts_code = k0.ts_code
          AND trade_date BETWEEN DATE_SUB(@td, INTERVAL 6 DAY) AND DATE_SUB(@td, INTERVAL 1 DAY)
    )
    AND k0.close < km1.close
    AND s.name NOT LIKE '%ST%';
```

#### E2-S3-T2 假突破

```yaml
判定:
  - T 日突破 60 日新高(已在 strong 池标记 breakout)
  - T+1 或 T+2 收盘 < 突破位
判定时机: T+2 收盘后(滞后 2 日)
signal_type: trap_false_breakout
```

```sql
-- 文件: sql/anomaly/05_trap_false_breakout.sql

INSERT INTO ads_l8_unified_signal (...)
SELECT
    @td, k.ts_code, s.name, s.industry_sw1, s.industry_sw3,
    'trap', 'trap_false_breakout', NULL,
    k.pct_chg, k.turnover_rate, k.vol / NULLIF(k.avg_vol_20d, 0),
    k.amount, mf.net_mf_amount,
    JSON_OBJECT(
        'trap_subtype',         'false_breakout',
        'breakout_date',        prev.trade_date,
        'breakout_high',        prev.high,
        'today_close',          k.close,
        'below_breakout_pct',   (k.close - prev.high) / prev.high
    ),
    LEAST(100, GREATEST(0, ABS((k.close - prev.high) / prev.high) * 800)),
    'v20260502'
FROM stock_kline_daily k
JOIN ads_l8_unified_signal prev
        ON prev.ts_code = k.ts_code
        AND prev.pool_type = 'strong'
        AND prev.signal_type = 'breakout'
        AND prev.trade_date BETWEEN DATE_SUB(@td, INTERVAL 2 DAY) AND DATE_SUB(@td, INTERVAL 1 DAY)
JOIN stock_basic_info s    ON s.ts_code = k.ts_code
LEFT JOIN ods_moneyflow_stock mf ON mf.ts_code = k.ts_code AND mf.trade_date = @td
WHERE
    k.trade_date = @td
    AND k.close < prev.high
    AND s.name NOT LIKE '%ST%';
```

#### E2-S3-T3 高位巨量出货

```yaml
判定:
  - 当日涨幅 > 7%
  - 当日量比 > 5
  - 收盘价 / 当日最高价 < 0.95
  - 60 日内累计涨幅 > 30%
判定时机: 当日盘后
signal_type: trap_high_vol_topping
```

```sql
-- 文件: sql/anomaly/05_trap_high_vol_topping.sql

INSERT INTO ads_l8_unified_signal (...)
SELECT
    @td, k.ts_code, s.name, s.industry_sw1, s.industry_sw3,
    'trap', 'trap_high_vol_topping', NULL,
    k.pct_chg, k.turnover_rate, k.vol / NULLIF(k.avg_vol_20d, 0),
    k.amount, mf.net_mf_amount,
    JSON_OBJECT(
        'trap_subtype',                'high_vol_topping',
        'intraday_drop_from_high',     (k.close - k.high) / k.high,
        'vol_ratio_today',             k.vol / NULLIF(k.avg_vol_20d, 0),
        'cumulative_60d_pct',          (k.close - k60.close) / k60.close
    ),
    LEAST(100, GREATEST(0, ABS((k.close - k.high) / k.high) * 1000)),
    'v20260502'
FROM stock_kline_daily k
JOIN stock_kline_daily k60 ON k60.ts_code = k.ts_code
                           AND k60.trade_date = DATE_SUB(@td, INTERVAL 60 DAY)
JOIN stock_basic_info s    ON s.ts_code = k.ts_code
LEFT JOIN ods_moneyflow_stock mf ON mf.ts_code = k.ts_code AND mf.trade_date = @td
WHERE
    k.trade_date = @td
    AND k.pct_chg > 0.07
    AND k.vol / NULLIF(k.avg_vol_20d, 0) > 5.0
    AND k.close / NULLIF(k.high, 0) < 0.95
    AND (k.close - k60.close) / k60.close > 0.30
    AND s.name NOT LIKE '%ST%';
```

#### E2-S3-T4 领涨股见顶

```yaml
判定:
  - 板块过去 20 日涨幅前 1 名个股
  - 该股近 5 日累计涨幅 < 0
  - 同期板块指数仍在 5 日新高
判定时机: 当日盘后
signal_type: trap_leader_topping
```

> **实施建议**:此判定需要"板块涨幅 Top 1 + 跨期对比",**Python 实现更直观**。逻辑见伪代码,详细脚本由 Antigravity 实现。

```python
# 文件: scripts/anomaly/trap_leader_topping.py

def detect_leader_topping(trade_date: str) -> pd.DataFrame:
    # 1. 找出每个行业过去 20 日涨幅 Top 1 的股票
    sector_leaders = ...
    
    # 2. 筛选近 5 日累计涨幅 < 0 的
    leaders_falling = sector_leaders[sector_leaders['ret_5d'] < 0]
    
    # 3. 对应板块指数仍在 5 日新高
    sector_still_strong = ...
    
    # 4. 取交集
    return leaders_falling.merge(sector_still_strong, on='industry_sw1')
```

#### E2-S3-AC 陷阱判定整体验收

> **Given** 当日有 3 只股满足"高位巨量出货"  
> **When** 执行 E2-S3-T3 SQL  
> **Then** `ads_l8_unified_signal` 中 `pool_type='trap' AND signal_type='trap_high_vol_topping'` 当日记录数 = 3,且每行 `signal_features.intraday_drop_from_high < -0.05`
