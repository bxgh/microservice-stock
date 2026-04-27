# 盘后复盘体系 · 第 3 + 4 章交付

> **范围:** L4 情绪与连板 + L3 资金流向
> **版本:** v1.0 · 2026-04-27
> **依赖前置:** 第 1 章(L1 + 涨跌停池)、第 2 章(L2 行业风格)
> **交付物:** 建表 SQL、计算 SQL、小程序前端、数据字典、字段映射

## 背景

第 3 章 L4 是盘后体系中最依赖第 1 章涨跌停池的层级,核心产出"次日打板预期",指标偏短线。第 4 章 L3 是中期资金验证层,五大资金流向(主力/北向/两融/ETF/龙虎榜)互相印证。两章数据互有依赖(L4 的 ERP 需要利率,L3 也用利率;L4 异象票判断需要 L3 的成交配合),合并交付。

## 目标

- L4:每日产出 1 行情绪综合指标,支持次日"高度板/晋级率/赚钱效应"判断
- L3:每日产出 1 行五大资金合成指标 + N 行行业资金/龙虎榜个股流水
- 前端:两个独立 tab,数据可在情绪页 ↔ 资金页交叉跳转
- 计算性能:每日批量 < 30 秒,支持 T+0 盘后 18:00 出数

## 范围

**包含:**
- 第 3 章 L4 情绪综合(连板梯队、晋级率、炸板率、赚钱效应、异象票、ERP)
- 第 4 章 L3 资金合成(主力净流入、北向估算、两融、ETF 净申购、龙虎榜、期指基差、大宗)
- 利率数据小规模引入(支撑 ERP 计算,完整版在第 7 章)

**非目标(明确不做):**
- 概念资金流(留在第 4 章扩展位,本期只到行业级)
- 港股通南向(放第 7 章)
- 龙虎榜机构席位画像(基础版仅做游资席位,机构画像 TBD)
- 期权 PCR / IV(放第 7 章)

---

## E1 第 3 章 · L4 情绪与连板

### 章节概览

| 项 | 数量 | 说明 |
|---|---|---|
| 新增 ODS 表 | 1 | `ods_yield_curve_daily`(小规模利率,7 章会扩展) |
| 新增 ADS 表 | 1 | `ads_l4_sentiment`(每日 1 行) |
| 复用表 | 4 | `ods_event_limit_pool` / `stock_kline_daily` / `daily_basic` / `trade_cal` |
| 前端页面 | 1 | `pages/sentiment/sentiment` |

数据流向:
```
ods_event_limit_pool ─┐
stock_kline_daily ────┼─→ ads_l4_sentiment
daily_basic ──────────┤
ods_yield_curve_daily ┘
```

### E1-S1 建表 SQL

**作为** 数据工程师,**我希望** 按规范建立 L4 情绪相关表,**以便** 计算 SQL 与前端有稳定 schema 契约。

#### E1-S1-T1 利率维表(支撑 ERP)

```sql
-- ====================================================================
-- ods_yield_curve_daily · 国债收益率曲线日度
-- 数据源: Tushare cn_gov_yield (TBD: 接口名称需 Antigravity 确认)
-- 频率: 每个交易日
-- 说明: 第 3 章先用 1y / 10y 两个关键期限,第 7 章扩展到完整曲线
-- ====================================================================
CREATE TABLE `ods_yield_curve_daily` (
  `trade_date`     DATE          NOT NULL                COMMENT '交易日',
  `term`           VARCHAR(8)    NOT NULL                COMMENT '期限: 1y/3y/5y/10y/30y',
  `yield_pct`      DECIMAL(10,6) NOT NULL                COMMENT '收益率(小数, 0.0265 = 2.65%)',
  `update_time`    DATETIME      NOT NULL                COMMENT '入库时间',
  PRIMARY KEY (`trade_date`, `term`),
  KEY `idx_term_date` (`term`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='国债收益率曲线 ODS,口径: 中债估值收盘到期收益率';
```

> **注意点:** `yield_pct` **必须存小数**,Tushare 原始返回若是百分比(如 2.65)需 `/100` 入库,与全库口径一致。

#### E1-S1-T2 L4 情绪指标主表

```sql
-- ====================================================================
-- ads_l4_sentiment · L4 情绪综合指标日度
-- 频率: 每个交易日 1 行
-- 计算时点: 盘后 17:30(等 ods_event_limit_pool 入库完成)
-- ====================================================================
CREATE TABLE `ads_l4_sentiment` (
  `trade_date`              DATE         NOT NULL            COMMENT '交易日',

  -- ===== 涨跌停基础统计 =====
  `limit_up_count`          INT          NOT NULL DEFAULT 0  COMMENT '涨停家数(剔除一字开板)',
  `limit_up_count_natural`  INT          NOT NULL DEFAULT 0  COMMENT '自然涨停家数(不剔除)',
  `limit_down_count`        INT          NOT NULL DEFAULT 0  COMMENT '跌停家数',
  `blast_count`             INT          NOT NULL DEFAULT 0  COMMENT '炸板家数(开板未封)',
  `blast_rate`              DECIMAL(10,6)         DEFAULT NULL COMMENT '炸板率 = blast / (limit_up + blast),小数',

  -- ===== 连板梯队 =====
  `board_ladder_json`       VARCHAR(500)          DEFAULT NULL COMMENT '连板梯队 JSON, 例: {"1":50,"2":12,"3":5,"4":2}',
  `max_board_height`        TINYINT      NOT NULL DEFAULT 0  COMMENT '最高连板数',
  `max_board_count`         INT          NOT NULL DEFAULT 0  COMMENT '最高连板梯队票数',
  `multi_board_count`       INT          NOT NULL DEFAULT 0  COMMENT '2 板及以上家数(连板梯队)',

  -- ===== 晋级率(今日 N 板 / 昨日 N-1 板) =====
  `promotion_rate_1to2`     DECIMAL(10,6)         DEFAULT NULL COMMENT '首板进 2 板晋级率',
  `promotion_rate_2to3`     DECIMAL(10,6)         DEFAULT NULL COMMENT '2 进 3 晋级率',
  `promotion_rate_3plus`    DECIMAL(10,6)         DEFAULT NULL COMMENT '3 板以上整体晋级率',

  -- ===== 赚钱效应(昨日涨停池今日表现) =====
  `yzt_today_avg_pct`       DECIMAL(10,6)         DEFAULT NULL COMMENT '昨日涨停今日平均涨幅(小数)',
  `yzt_red_rate`            DECIMAL(10,6)         DEFAULT NULL COMMENT '昨日涨停今日红盘率',
  `yzt_again_rate`          DECIMAL(10,6)         DEFAULT NULL COMMENT '昨日涨停今日继续涨停率',
  `yzt_sample_count`        INT                   DEFAULT NULL COMMENT '昨日涨停样本数',

  -- ===== 异象票 =====
  `one_word_zt_count`       INT          NOT NULL DEFAULT 0  COMMENT '一字板(开盘即涨停且未开板)',
  `t_b_count`               INT          NOT NULL DEFAULT 0  COMMENT '天地板(高开/盘中涨停 → 跌停)',
  `b_t_count`               INT          NOT NULL DEFAULT 0  COMMENT '地天板(跌停 → 涨停)',

  -- ===== 中期情绪(估值/利率派生) =====
  `dividend_yield_hs300`    DECIMAL(10,6)         DEFAULT NULL COMMENT '沪深 300 股息率(TTM,小数)',
  `yield_10y`               DECIMAL(10,6)         DEFAULT NULL COMMENT '10 年国债收益率(小数)',
  `erp_value`               DECIMAL(10,6)         DEFAULT NULL COMMENT 'ERP = 1/PE - 10y, 小数',
  `erp_pctile_10y`          DECIMAL(6,4)          DEFAULT NULL COMMENT 'ERP 10 年分位数(0-1)',
  `div_minus_yield_10y`     DECIMAL(10,6)         DEFAULT NULL COMMENT '股息率 - 10y 利差',

  -- ===== 综合评分 =====
  `sentiment_score`         DECIMAL(6,2)          DEFAULT NULL COMMENT '综合情绪评分 0-100',
  `sentiment_label`         VARCHAR(16)           DEFAULT NULL COMMENT '情绪标签: 冰点/低迷/中性/活跃/亢奋',

  `update_time`             DATETIME     NOT NULL            COMMENT '入库时间',
  PRIMARY KEY (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='L4 情绪与连板综合指标';
```

#### E1-S1-T1-AC 验收标准

> **Given** 表创建语句执行成功
> **When** 查询 `INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='ads_l4_sentiment'`
> **Then** 字段总数 = 25,所有比率字段类型为 `DECIMAL(10,6)`,主键唯一

> **Given** 灌入连续 10 个交易日数据
> **When** `SELECT COUNT(*) FROM ads_l4_sentiment WHERE trade_date BETWEEN ... AND ...`
> **Then** 返回 = 10,无重复主键

---

### E1-S2 计算 SQL

**作为** 数据工程师,**我希望** 一套幂等的 INSERT...ON DUPLICATE KEY UPDATE 计算 SQL,**以便** 每日盘后批跑可重复执行。

#### E1-S2-T1 连板梯队聚合(MySQL 5.7 兼容)

```sql
-- 输入参数: @td (目标交易日), @td_prev (前一交易日,从 trade_cal 取)

-- 步骤 1: 取连板梯队 + 各项基础统计
-- MySQL 5.7 没有 JSON_OBJECTAGG, 用 GROUP_CONCAT 拼 JSON 字符串
SET @td := '2026-04-27';

SELECT t.cal_date INTO @td_prev
FROM trade_cal t
WHERE t.cal_date < @td AND t.is_open = 1
ORDER BY t.cal_date DESC LIMIT 1;
```

```sql
-- 步骤 2: 主计算 INSERT
INSERT INTO ads_l4_sentiment (
  trade_date,
  limit_up_count, limit_up_count_natural, limit_down_count,
  blast_count, blast_rate,
  board_ladder_json, max_board_height, max_board_count, multi_board_count,
  one_word_zt_count, t_b_count, b_t_count,
  update_time
)
SELECT
  @td AS trade_date,

  -- 涨停家数(剔除一字开板,以 board_height >= 1 计)
  SUM(CASE WHEN pool_type = 'zt' AND open_times > 0 THEN 1 ELSE 0 END)
    AS limit_up_count,
  SUM(CASE WHEN pool_type = 'zt' THEN 1 ELSE 0 END)
    AS limit_up_count_natural,
  SUM(CASE WHEN pool_type = 'dt' THEN 1 ELSE 0 END)
    AS limit_down_count,

  -- 炸板
  SUM(CASE WHEN pool_type = 'zb' THEN 1 ELSE 0 END) AS blast_count,
  CASE
    WHEN SUM(CASE WHEN pool_type IN ('zt','zb') THEN 1 ELSE 0 END) = 0 THEN NULL
    ELSE SUM(CASE WHEN pool_type='zb' THEN 1 ELSE 0 END)
       / SUM(CASE WHEN pool_type IN ('zt','zb') THEN 1 ELSE 0 END)
  END AS blast_rate,

  -- 连板梯队 JSON(子查询拼接)
  (SELECT CONCAT('{',
            GROUP_CONCAT(CONCAT('"', board_height, '":', cnt)
                         ORDER BY board_height SEPARATOR ','),
          '}')
   FROM (
     SELECT board_height, COUNT(*) AS cnt
     FROM ods_event_limit_pool
     WHERE trade_date = @td AND pool_type = 'zt' AND board_height >= 1
     GROUP BY board_height
   ) ladder) AS board_ladder_json,

  -- 最高板 + 最高板票数
  MAX(CASE WHEN pool_type = 'zt' THEN board_height ELSE 0 END) AS max_board_height,
  SUM(CASE WHEN pool_type = 'zt'
            AND board_height = (SELECT MAX(board_height)
                                FROM ods_event_limit_pool
                                WHERE trade_date = @td AND pool_type='zt')
           THEN 1 ELSE 0 END) AS max_board_count,
  -- 2 板及以上
  SUM(CASE WHEN pool_type = 'zt' AND board_height >= 2 THEN 1 ELSE 0 END)
    AS multi_board_count,

  -- 异象票
  SUM(CASE WHEN pool_type = 'zt' AND open_times = 0 THEN 1 ELSE 0 END)
    AS one_word_zt_count,
  -- 天地板/地天板需要从 stock_kline_daily 派生,见步骤 3

  0 AS t_b_count,  -- 占位,见步骤 3 UPDATE
  0 AS b_t_count,
  NOW() AS update_time

FROM ods_event_limit_pool
WHERE trade_date = @td

ON DUPLICATE KEY UPDATE
  limit_up_count         = VALUES(limit_up_count),
  limit_up_count_natural = VALUES(limit_up_count_natural),
  limit_down_count       = VALUES(limit_down_count),
  blast_count            = VALUES(blast_count),
  blast_rate             = VALUES(blast_rate),
  board_ladder_json      = VALUES(board_ladder_json),
  max_board_height       = VALUES(max_board_height),
  max_board_count        = VALUES(max_board_count),
  multi_board_count      = VALUES(multi_board_count),
  one_word_zt_count      = VALUES(one_word_zt_count),
  update_time            = NOW();
```

#### E1-S2-T2 天地板 / 地天板补算

```sql
-- 天地板: 当日最高价 = 涨停价, 收盘 = 跌停价
-- 地天板: 当日最低价 = 跌停价, 收盘 = 涨停价
-- 涨停价 = 昨收 × 1.10 (主板) / 1.20 (科创、创业、北证)
-- 简化口径: |high - high_limit| / pre_close < 0.001 即视为触板
-- 注: stock_kline_daily.code 不带后缀, ts_code 形式需自行拼接

UPDATE ads_l4_sentiment a
JOIN (
  SELECT
    k.trade_date,
    SUM(CASE
          WHEN k.high  >= k.pre_close * lim.up_ratio   * 0.9999
           AND k.close <= k.pre_close * lim.down_ratio * 1.0001
          THEN 1 ELSE 0 END) AS t_b,
    SUM(CASE
          WHEN k.low   <= k.pre_close * lim.down_ratio * 1.0001
           AND k.close >= k.pre_close * lim.up_ratio   * 0.9999
          THEN 1 ELSE 0 END) AS b_t
  FROM stock_kline_daily k
  JOIN stock_basic_info b ON b.symbol = k.code
  JOIN (
    -- 涨跌幅限制映射
    SELECT '主板' AS market, 1.10 AS up_ratio, 0.90 AS down_ratio
    UNION ALL SELECT '创业板', 1.20, 0.80
    UNION ALL SELECT '科创板', 1.20, 0.80
    UNION ALL SELECT '北交所', 1.30, 0.70
  ) lim ON lim.market = b.market
  WHERE k.trade_date = @td
    AND b.list_status = 'L'
    AND b.name NOT LIKE '%ST%'   -- ST 价格限制 5%, 暂不纳入异象
  GROUP BY k.trade_date
) tb ON tb.trade_date = a.trade_date
SET a.t_b_count = tb.t_b,
    a.b_t_count = tb.b_t;
```

> **TBD:** `stock_basic_info.market` 字段值是否真的为「主板/创业板/科创板/北交所」需 Antigravity 确认;若是 `MAIN/STAR/GEM/BSE` 等代号,JOIN 条件需调整。

#### E1-S2-T3 晋级率计算

```sql
-- 晋级率: 今日 N 板及以上家数 / 昨日 (N-1) 板及以上家数
-- 用变量模拟 LAG, 避免窗口函数

UPDATE ads_l4_sentiment a
JOIN (
  SELECT
    today.trade_date,
    -- 1 进 2: 今日 2 板 / 昨日首板
    CASE WHEN yest_1b > 0 THEN today_2b / yest_1b ELSE NULL END AS p_1to2,
    -- 2 进 3: 今日 3 板 / 昨日 2 板
    CASE WHEN yest_2b > 0 THEN today_3b / yest_2b ELSE NULL END AS p_2to3,
    -- 3+: 今日 4 板及以上 / 昨日 3 板及以上
    CASE WHEN yest_3b > 0 THEN today_4b / yest_3b ELSE NULL END AS p_3plus
  FROM (
    SELECT
      @td AS trade_date,
      SUM(CASE WHEN today.board_height = 2 THEN 1 ELSE 0 END) AS today_2b,
      SUM(CASE WHEN today.board_height = 3 THEN 1 ELSE 0 END) AS today_3b,
      SUM(CASE WHEN today.board_height >= 4 THEN 1 ELSE 0 END) AS today_4b,
      (SELECT COUNT(*) FROM ods_event_limit_pool
       WHERE trade_date = @td_prev AND pool_type='zt' AND board_height = 1) AS yest_1b,
      (SELECT COUNT(*) FROM ods_event_limit_pool
       WHERE trade_date = @td_prev AND pool_type='zt' AND board_height = 2) AS yest_2b,
      (SELECT COUNT(*) FROM ods_event_limit_pool
       WHERE trade_date = @td_prev AND pool_type='zt' AND board_height >= 3) AS yest_3b
    FROM ods_event_limit_pool today
    WHERE today.trade_date = @td AND today.pool_type = 'zt'
  ) today
) p ON p.trade_date = a.trade_date
SET a.promotion_rate_1to2  = p.p_1to2,
    a.promotion_rate_2to3  = p.p_2to3,
    a.promotion_rate_3plus = p.p_3plus;
```

#### E1-S2-T4 赚钱效应(昨日涨停今日表现)

```sql
-- 昨日涨停池 JOIN 今日 K 线
-- 注意: ods_event_limit_pool.ts_code 带后缀, stock_kline_daily.code 不带后缀

UPDATE ads_l4_sentiment a
JOIN (
  SELECT
    @td AS trade_date,
    AVG(k.pct_chg)                                          AS avg_pct,
    SUM(CASE WHEN k.pct_chg > 0 THEN 1 ELSE 0 END) / COUNT(*) AS red_rate,
    SUM(CASE WHEN k.pct_chg >= 0.097 THEN 1 ELSE 0 END) / COUNT(*) AS again_rate,
    COUNT(*)                                                AS sample_cnt
  FROM ods_event_limit_pool y
  JOIN stock_kline_daily k
    ON SUBSTRING(y.ts_code, 1, 6) = k.code
   AND k.trade_date = @td
  WHERE y.trade_date = @td_prev
    AND y.pool_type = 'zt'
) e ON e.trade_date = a.trade_date
SET a.yzt_today_avg_pct = e.avg_pct,
    a.yzt_red_rate      = e.red_rate,
    a.yzt_again_rate    = e.again_rate,
    a.yzt_sample_count  = e.sample_cnt;
```

> **口径说明:** `pct_chg >= 0.097` 是 9.7% 阈值,容差 0.3% 应对停牌复牌后小幅折价等边缘情况。主板取 9.7,创业板/科创板需要单独阈值 ≥ 0.197,本期为简化先统一 9.7%,**前端展示需注明此口径**(后续优化项 TBD)。

#### E1-S2-T5 中期情绪(ERP)

```sql
-- ERP = 沪深 300 滚动 PE 倒数 - 10 年国债收益率
-- 数据源: daily_basic 取 000300.SH 的 pe_ttm; ods_yield_curve_daily 取 10y

UPDATE ads_l4_sentiment a
JOIN (
  SELECT
    @td AS trade_date,
    -- 沪深 300 股息率: 取成分股加权,简化版直接用 daily_basic.dv_ratio 的市值加权
    -- 完整加权计算放第 5 章估值层,本章先用 000300.SH 指数级 dv_ratio 占位
    (SELECT db.dv_ttm / 100  -- Tushare dv_ttm 是百分比, /100 转小数
     FROM daily_basic db
     WHERE db.ts_code = '000300.SH' AND db.trade_date = @td LIMIT 1) AS div_y,
    (SELECT yc.yield_pct
     FROM ods_yield_curve_daily yc
     WHERE yc.term = '10y' AND yc.trade_date = @td LIMIT 1)         AS y10,
    (SELECT 1.0 / db.pe_ttm
     FROM daily_basic db
     WHERE db.ts_code = '000300.SH' AND db.trade_date = @td LIMIT 1) AS earnings_y
) m ON m.trade_date = a.trade_date
SET a.dividend_yield_hs300 = m.div_y,
    a.yield_10y            = m.y10,
    a.erp_value            = m.earnings_y - m.y10,
    a.div_minus_yield_10y  = m.div_y - m.y10;
```

```sql
-- ERP 10 年分位数(滚动计算,排序定位)
-- MySQL 5.7 无 PERCENT_RANK, 用 COUNT 比较实现

UPDATE ads_l4_sentiment a
JOIN (
  SELECT
    @td AS trade_date,
    (SELECT COUNT(*) FROM ads_l4_sentiment a2
     WHERE a2.trade_date BETWEEN DATE_SUB(@td, INTERVAL 10 YEAR) AND @td
       AND a2.erp_value IS NOT NULL
       AND a2.erp_value < (SELECT erp_value FROM ads_l4_sentiment WHERE trade_date = @td)
    ) /
    NULLIF((SELECT COUNT(*) FROM ads_l4_sentiment a2
     WHERE a2.trade_date BETWEEN DATE_SUB(@td, INTERVAL 10 YEAR) AND @td
       AND a2.erp_value IS NOT NULL), 0) AS pctile
) p ON p.trade_date = a.trade_date
SET a.erp_pctile_10y = p.pctile;
```

> **冷启动注意:** 历史 < 10 年时,分位数样本不足,前端展示需附「历史样本: N 个」标注。Antigravity 回补时 `daily_basic.000300.SH` 至少需要 10 年(2016 至今)才能让分位数稳定。

#### E1-S2-T6 综合评分(简化版)

```sql
-- 0-100 评分, 6 个子项加权
-- 可调权: 涨停 25% / 连板高度 20% / 晋级率 20% / 赚钱效应 20% / 炸板率(逆) 10% / ERP 5%

UPDATE ads_l4_sentiment a
SET
  a.sentiment_score = ROUND(
      LEAST(100, a.limit_up_count / 100 * 100) * 0.25
    + LEAST(100, a.max_board_height / 8 * 100) * 0.20
    + COALESCE(a.promotion_rate_2to3, 0) * 100 * 0.20
    + LEAST(100, GREATEST(0, (COALESCE(a.yzt_today_avg_pct, 0) + 0.05) / 0.10 * 100)) * 0.20
    + (100 - LEAST(100, COALESCE(a.blast_rate, 0) * 200)) * 0.10
    + COALESCE(a.erp_pctile_10y, 0.5) * 100 * 0.05
  , 2),
  a.sentiment_label = CASE
    WHEN a.sentiment_score >= 80 THEN '亢奋'
    WHEN a.sentiment_score >= 60 THEN '活跃'
    WHEN a.sentiment_score >= 40 THEN '中性'
    WHEN a.sentiment_score >= 20 THEN '低迷'
    ELSE '冰点'
  END
WHERE a.trade_date = @td;
```

> **Trade-off:** 评分公式为初版,**权重锁定后避免频繁调整**(否则历史时序失去可比性)。后续若调整,需建版本表 `ads_l4_sentiment_v2`,前端提供版本切换。

#### E1-S2-T*-AC 验收标准

> **Given** `ods_event_limit_pool` 中 2026-04-27 有 50 个 zt + 5 个 zb + 8 个 dt
> **When** 执行 E1-S2-T1
> **Then** `ads_l4_sentiment.limit_up_count_natural = 50`,`blast_rate ≈ 0.0909`(5/55)

> **Given** 历史 ERP 序列 < 100 个样本
> **When** 执行 E1-S2-T5
> **Then** `erp_pctile_10y` 仍可计算,前端需识别样本不足并降级显示

---

### E1-S3 微信小程序前端

**作为** 用户,**我希望** 在情绪页一屏看到当日连板格局、晋级率、赚钱效应,**以便** 快速判断次日打板预期。

#### E1-S3-T1 页面结构

```
pages/sentiment/sentiment
├── sentiment.json
├── sentiment.wxml
├── sentiment.wxss
└── sentiment.js
```

页面区块自上而下:
1. 顶部情绪温度计(综合评分 0-100 + 文字标签)
2. 连板梯队卡(柱状图 + 最高板数字大字)
3. 晋级率 / 炸板率三宫格
4. 赚钱效应卡(昨日涨停今日表现)
5. 异象票卡(一字 / 天地 / 地天)
6. 中期情绪卡(ERP + 分位数)

#### E1-S3-T2 wxml

```xml
<!-- pages/sentiment/sentiment.wxml -->
<view class="page-wrap">

  <!-- 顶部日期 + 综合评分 -->
  <view class="hero">
    <view class="hero-meta">
      <text class="hero-date mono">{{trade_date}}</text>
      <text class="hero-cn">情绪综合</text>
    </view>
    <view class="hero-score">
      <text class="score-num mono">{{sentiment_score}}</text>
      <text class="score-label">{{sentiment_label}}</text>
    </view>
    <view class="hero-side-bar"></view>
  </view>

  <!-- 连板梯队 -->
  <view class="card">
    <view class="card-side-bar"></view>
    <view class="card-header">
      <text class="card-title-cn">连板梯队</text>
      <text class="card-title-en">BOARD LADDER</text>
    </view>
    <view class="ladder-grid">
      <view class="ladder-item" wx:for="{{board_ladder}}" wx:key="height">
        <text class="ladder-height mono">{{item.height}}板</text>
        <view class="ladder-bar" style="height: {{item.bar_height}}rpx;"></view>
        <text class="ladder-cnt mono">{{item.cnt}}</text>
      </view>
    </view>
    <view class="ladder-summary">
      <view class="kv">
        <text class="kv-k">最高板</text>
        <text class="kv-v mono up">{{max_board_height}}板</text>
      </view>
      <view class="kv">
        <text class="kv-k">连板数</text>
        <text class="kv-v mono">{{multi_board_count}}</text>
      </view>
      <view class="kv">
        <text class="kv-k">涨停</text>
        <text class="kv-v mono up">{{limit_up_count_natural}}</text>
      </view>
      <view class="kv">
        <text class="kv-k">跌停</text>
        <text class="kv-v mono down">{{limit_down_count}}</text>
      </view>
    </view>
  </view>

  <!-- 晋级率 / 炸板率 -->
  <view class="card">
    <view class="card-side-bar"></view>
    <view class="card-header">
      <text class="card-title-cn">晋级与炸板</text>
      <text class="card-title-en">PROMOTION · BLAST</text>
    </view>
    <view class="rate-grid">
      <view class="rate-cell">
        <text class="rate-cn">1 进 2</text>
        <text class="rate-num mono">{{promotion_rate_1to2_pct}}<text class="unit">%</text></text>
      </view>
      <view class="rate-cell">
        <text class="rate-cn">2 进 3</text>
        <text class="rate-num mono">{{promotion_rate_2to3_pct}}<text class="unit">%</text></text>
      </view>
      <view class="rate-cell">
        <text class="rate-cn">3+ 整体</text>
        <text class="rate-num mono">{{promotion_rate_3plus_pct}}<text class="unit">%</text></text>
      </view>
      <view class="rate-cell warn">
        <text class="rate-cn">炸板率</text>
        <text class="rate-num mono">{{blast_rate_pct}}<text class="unit">%</text></text>
      </view>
    </view>
  </view>

  <!-- 赚钱效应 -->
  <view class="card">
    <view class="card-side-bar"></view>
    <view class="card-header">
      <text class="card-title-cn">赚钱效应</text>
      <text class="card-title-en">YESTERDAY'S WINNERS</text>
    </view>
    <view class="effect-row">
      <view class="effect-item">
        <text class="effect-cn">昨涨停今平均涨幅</text>
        <text class="effect-num mono {{yzt_today_avg_pct >= 0 ? 'up' : 'down'}}">
          {{yzt_today_avg_pct >= 0 ? '↑' : '↓'}}{{yzt_today_avg_pct_pct}}%
        </text>
      </view>
      <view class="effect-item">
        <text class="effect-cn">红盘率</text>
        <text class="effect-num mono">{{yzt_red_rate_pct}}%</text>
      </view>
      <view class="effect-item">
        <text class="effect-cn">连续涨停率</text>
        <text class="effect-num mono up">{{yzt_again_rate_pct}}%</text>
      </view>
      <view class="effect-meta">
        <text class="meta-text">样本 {{yzt_sample_count}} 只 · ≥9.7% 计入连板</text>
      </view>
    </view>
  </view>

  <!-- 异象票 -->
  <view class="card">
    <view class="card-side-bar"></view>
    <view class="card-header">
      <text class="card-title-cn">异象板</text>
      <text class="card-title-en">EXTREMES</text>
    </view>
    <view class="extreme-grid">
      <view class="ex-cell">
        <text class="ex-cn">一字板</text>
        <text class="ex-num mono">{{one_word_zt_count}}</text>
      </view>
      <view class="ex-cell weak">
        <text class="ex-cn">天地板</text>
        <text class="ex-num mono">{{t_b_count}}</text>
      </view>
      <view class="ex-cell strong">
        <text class="ex-cn">地天板</text>
        <text class="ex-num mono">{{b_t_count}}</text>
      </view>
    </view>
  </view>

  <!-- 中期情绪 ERP -->
  <view class="card">
    <view class="card-side-bar"></view>
    <view class="card-header">
      <text class="card-title-cn">中期情绪</text>
      <text class="card-title-en">EQUITY RISK PREMIUM</text>
    </view>
    <view class="erp-row">
      <view class="erp-main">
        <text class="erp-num mono">{{erp_value_pct}}<text class="unit">%</text></text>
        <text class="erp-label">ERP 值</text>
      </view>
      <view class="erp-pctile">
        <text class="pctile-num mono">{{erp_pctile_10y_pct}}<text class="unit">%</text></text>
        <text class="pctile-label">10 年分位</text>
      </view>
    </view>
    <view class="erp-detail">
      <view class="kv">
        <text class="kv-k">沪深 300 股息率</text>
        <text class="kv-v mono">{{dividend_yield_hs300_pct}}%</text>
      </view>
      <view class="kv">
        <text class="kv-k">10 年国债</text>
        <text class="kv-v mono">{{yield_10y_pct}}%</text>
      </view>
      <view class="kv">
        <text class="kv-k">股债利差</text>
        <text class="kv-v mono">{{div_minus_yield_10y_pct}}%</text>
      </view>
    </view>
  </view>

</view>
```

#### E1-S3-T3 wxss(沿用第 1/2 章设计系统)

```css
/* pages/sentiment/sentiment.wxss */
@import "/styles/tokens.wxss";  /* 假设全局样式变量已抽离 */

.page-wrap { padding: 16rpx; background: var(--bg); min-height: 100vh; }

/* ========== Hero ========== */
.hero {
  position: relative;
  background: var(--bg-card);
  padding: 32rpx 32rpx 32rpx 40rpx;
  margin-bottom: 16rpx;
  border-radius: 4rpx;
  display: flex; justify-content: space-between; align-items: center;
}
.hero-side-bar {
  position: absolute; top: 32rpx; bottom: 32rpx; left: 0;
  width: 6rpx; background: var(--amber);
}
.hero-date { color: var(--ink-dim); font-size: var(--fs-aux); letter-spacing: 2rpx; }
.hero-cn { display: block; color: var(--ink); font-size: var(--fs-title); font-weight: 600; margin-top: 8rpx; }
.hero-score { text-align: right; }
.score-num { font-size: 88rpx; color: var(--amber); font-weight: 700; line-height: 1; }
.score-label { display: block; color: var(--ink-dim); font-size: var(--fs-body); margin-top: 8rpx; }

/* ========== 连板梯队 ========== */
.ladder-grid {
  display: flex; align-items: flex-end; justify-content: space-around;
  height: 240rpx; padding: 16rpx 0; border-bottom: 1rpx solid var(--hair);
}
.ladder-item { display: flex; flex-direction: column; align-items: center; gap: 8rpx; }
.ladder-height { color: var(--ink-dim); font-size: var(--fs-aux); }
.ladder-bar {
  width: 32rpx; min-height: 4rpx; background: var(--up);
  box-shadow: 0 0 8rpx rgba(229, 100, 79, 0.4);
}
.ladder-cnt { color: var(--ink); font-size: var(--fs-data); }
.ladder-summary {
  display: grid; grid-template-columns: repeat(4, 1fr);
  padding: 24rpx 0 0; gap: 16rpx;
}
.kv { display: flex; flex-direction: column; gap: 6rpx; }
.kv-k { color: var(--ink-mute); font-size: var(--fs-aux); }
.kv-v { font-size: var(--fs-data); color: var(--ink); }

/* ========== 晋级率三宫格 ========== */
.rate-grid {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 1rpx; background: var(--hair);
}
.rate-cell {
  background: var(--bg-card); padding: 24rpx 16rpx;
  display: flex; flex-direction: column; align-items: center; gap: 12rpx;
}
.rate-cn { color: var(--ink-dim); font-size: var(--fs-aux); letter-spacing: 2rpx; }
.rate-num { font-size: 44rpx; color: var(--ink); font-weight: 600; }
.rate-cell.warn .rate-num { color: var(--alert); }
.unit { font-size: 22rpx; color: var(--ink-mute); margin-left: 4rpx; }

/* ========== 赚钱效应 ========== */
.effect-row { display: flex; flex-wrap: wrap; gap: 16rpx; }
.effect-item { flex: 1; min-width: 200rpx; }
.effect-cn { display: block; color: var(--ink-dim); font-size: var(--fs-aux); margin-bottom: 8rpx; }
.effect-num { font-size: 36rpx; }
.effect-meta { width: 100%; margin-top: 16rpx; padding-top: 16rpx; border-top: 1rpx solid var(--hair); }
.meta-text { color: var(--ink-mute); font-size: 22rpx; }

/* ========== 异象 ========== */
.extreme-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rpx; background: var(--hair); }
.ex-cell {
  background: var(--bg-card); padding: 24rpx 16rpx;
  display: flex; flex-direction: column; align-items: center; gap: 8rpx;
}
.ex-cn { color: var(--ink-dim); font-size: var(--fs-aux); }
.ex-num { font-size: 44rpx; color: var(--amber); font-weight: 600; }
.ex-cell.weak .ex-num { color: var(--weak); }
.ex-cell.strong .ex-num { color: var(--strong); }

/* ========== ERP ========== */
.erp-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16rpx 0; border-bottom: 1rpx solid var(--hair);
}
.erp-main, .erp-pctile { display: flex; flex-direction: column; }
.erp-num { font-size: 56rpx; color: var(--amber-bright); font-weight: 700; }
.erp-label, .pctile-label { color: var(--ink-mute); font-size: var(--fs-aux); margin-top: 4rpx; }
.pctile-num { font-size: 44rpx; color: var(--ink); }
.erp-detail {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 16rpx;
  padding-top: 24rpx;
}
```

#### E1-S3-T4 数据接口契约

```yaml
# 接口: GET /api/sentiment/daily?trade_date=2026-04-27
# 后端从 ads_l4_sentiment 单行查询并做单位转换(小数→百分比)
response:
  code: 0
  data:
    trade_date: "2026-04-27"
    sentiment_score: 72.50
    sentiment_label: "活跃"

    # 涨跌停
    limit_up_count: 48
    limit_up_count_natural: 53
    limit_down_count: 8
    blast_count: 12
    blast_rate_pct: 18.46     # 后端已 ×100

    # 连板梯队(数组,前端柱图直接消费)
    board_ladder:
      - { height: 1, cnt: 30, bar_height: 200 }   # bar_height = cnt / max(cnt) × 200
      - { height: 2, cnt: 12, bar_height: 80 }
      - { height: 3, cnt: 5,  bar_height: 33 }
      - { height: 4, cnt: 2,  bar_height: 13 }
    max_board_height: 4
    max_board_count: 2
    multi_board_count: 19

    # 晋级
    promotion_rate_1to2_pct: 24.50
    promotion_rate_2to3_pct: 41.67
    promotion_rate_3plus_pct: 40.00

    # 赚钱效应
    yzt_today_avg_pct: 0.0123        # 原始小数,前端判定颜色用
    yzt_today_avg_pct_pct: 1.23      # 显示用百分比
    yzt_red_rate_pct: 65.30
    yzt_again_rate_pct: 12.50
    yzt_sample_count: 48

    # 异象
    one_word_zt_count: 5
    t_b_count: 1
    b_t_count: 0

    # ERP
    erp_value_pct: 4.85
    erp_pctile_10y_pct: 78.20
    dividend_yield_hs300_pct: 2.95
    yield_10y_pct: 1.65
    div_minus_yield_10y_pct: 1.30
```

> **接口设计原则:** 后端做小数 → 百分比转换(字段加 `_pct` 后缀),前端纯展示不做计算。但保留原始小数(如 `yzt_today_avg_pct`)用于判定颜色(>0 为红、<0 为绿)。

---

### E1-S4 数据字典片段

#### `ods_yield_curve_daily`

| 字段 | 类型 | 单位 | 口径 | 备注 |
|---|---|---|---|---|
| trade_date | DATE | - | 交易日 | 与 trade_cal 对齐 |
| term | VARCHAR(8) | - | 期限 | `1y/3y/5y/10y/30y` |
| yield_pct | DECIMAL(10,6) | 小数 | 中债估值收盘到期收益率 | `0.0265 = 2.65%` |

#### `ads_l4_sentiment` 关键字段

| 字段 | 类型 | 单位 | 口径 |
|---|---|---|---|
| limit_up_count | INT | 只 | 剔除一字开盘的涨停家数 |
| limit_up_count_natural | INT | 只 | 自然涨停(含一字) |
| blast_rate | DECIMAL(10,6) | 小数 | `blast / (zt + blast)` |
| board_ladder_json | VARCHAR | JSON 字符串 | `{"1":50,"2":12,...}` |
| max_board_height | TINYINT | 板 | 最高连板数 |
| promotion_rate_2to3 | DECIMAL(10,6) | 小数 | `今日 3 板数 / 昨日 2 板数` |
| yzt_today_avg_pct | DECIMAL(10,6) | 小数 | 昨日涨停今日 pct_chg 算术平均 |
| yzt_again_rate | DECIMAL(10,6) | 小数 | 阈值 9.7%,所有市场统一(简化口径) |
| t_b_count / b_t_count | INT | 只 | 排除 ST,容差 0.01% |
| erp_value | DECIMAL(10,6) | 小数 | `1/PE_TTM(000300) - yield_10y` |
| erp_pctile_10y | DECIMAL(6,4) | 小数 | 10 年滚动百分位,样本不足时降级 |
| sentiment_score | DECIMAL(6,2) | 0-100 | 6 项加权,公式见 E1-S2-T6 |

---

### E1-S5 字段映射(数据源 → DB)

#### Tushare → `ods_yield_curve_daily`

| Tushare 字段 | DB 字段 | 处理 |
|---|---|---|
| `date` | `trade_date` | 直接 |
| (期限,接口返回多列) | `term` | 拆列为行,如 `_10y` 列 → `term='10y'` |
| `_10y` 列 | `yield_pct` | **`/100` 转小数** |

> **接口名称 TBD:** Tushare `cn_gov_yield` 或 `bond_yield` 需 Antigravity 实测确认。

#### 派生表无外部数据源映射,均从 ODS 计算

---

## E2 第 4 章 · L3 资金流向

### 章节概览

| 项 | 数量 | 说明 |
|---|---|---|
| 新增 ODS 表 | 5 | 个股资金流 / 沪深港通 / 龙虎榜营业部 / ETF 份额 / 期货日线 |
| 新增 DIM 表 | 2 | `fut_basic` 期货合约 / `dim_yz_seat` 游资席位 |
| 新增 ADS 表 | 2 | `ads_l3_capital_flow`(每日 1 行总览)/ `ads_l3_lhb_stock`(每日 N 行龙虎榜个股) |
| 复用表 | 3 | `stock_block_trade` / `market_margin_summary` / `north_capital_daily` |
| 前端页面 | 1 | `pages/capital/capital` |

### E2-S1 建表 SQL

#### E2-S1-T1 个股资金流(Tushare moneyflow)

```sql
-- ====================================================================
-- ods_moneyflow_stock · 个股资金流向(主力/超大单/大单/中单/小单)
-- 数据源: Tushare moneyflow
-- 频率: 每个交易日, 5400+ 只 × 1 行 ≈ 5400/日
-- 单位口径: Tushare 原值千元/万元 → 入库统一转元
-- ====================================================================
CREATE TABLE `ods_moneyflow_stock` (
  `trade_date`        DATE          NOT NULL          COMMENT '交易日',
  `ts_code`           VARCHAR(16)   NOT NULL          COMMENT '股票代码,带后缀',

  -- 主力资金(超大单 + 大单)净流入,元
  `net_mf_amount`     DECIMAL(20,2)          DEFAULT NULL COMMENT '主力净流入额,元',

  -- 单位: 笔数
  `buy_lg_vol`        INT                    DEFAULT NULL COMMENT '大单买入手数',
  `sell_lg_vol`       INT                    DEFAULT NULL COMMENT '大单卖出手数',
  `buy_elg_vol`       INT                    DEFAULT NULL COMMENT '超大单买入手数',
  `sell_elg_vol`      INT                    DEFAULT NULL COMMENT '超大单卖出手数',

  -- 各档资金(元)
  `buy_lg_amount`     DECIMAL(20,2)          DEFAULT NULL COMMENT '大单买入额,元',
  `sell_lg_amount`    DECIMAL(20,2)          DEFAULT NULL COMMENT '大单卖出额,元',
  `buy_elg_amount`    DECIMAL(20,2)          DEFAULT NULL COMMENT '超大单买入额,元',
  `sell_elg_amount`   DECIMAL(20,2)          DEFAULT NULL COMMENT '超大单卖出额,元',
  `buy_md_amount`     DECIMAL(20,2)          DEFAULT NULL COMMENT '中单买入额,元',
  `sell_md_amount`    DECIMAL(20,2)          DEFAULT NULL COMMENT '中单卖出额,元',
  `buy_sm_amount`     DECIMAL(20,2)          DEFAULT NULL COMMENT '小单买入额,元',
  `sell_sm_amount`    DECIMAL(20,2)          DEFAULT NULL COMMENT '小单卖出额,元',

  `update_time`       DATETIME      NOT NULL          COMMENT '入库时间',
  PRIMARY KEY (`trade_date`, `ts_code`),
  KEY `idx_ts_date` (`ts_code`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='个股资金流(主力/超大/大/中/小),元,Tushare moneyflow';
```

#### E2-S1-T2 沪深港通日度(Tushare moneyflow_hsgt)

```sql
-- ====================================================================
-- ods_moneyflow_hsgt · 沪深港通日度资金
-- 数据源: Tushare moneyflow_hsgt
-- 频率: 每个交易日 1 行
-- 注: 2024-08 后港交所收盘后才公布个股持股,日内净买入仍可用
-- ====================================================================
CREATE TABLE `ods_moneyflow_hsgt` (
  `trade_date`        DATE          NOT NULL          COMMENT '交易日',
  `ggt_ss`            DECIMAL(20,2)          DEFAULT NULL COMMENT '港股通(上,沪)成交净买入,元',
  `ggt_sz`            DECIMAL(20,2)          DEFAULT NULL COMMENT '港股通(深)成交净买入,元',
  `hgt`               DECIMAL(20,2)          DEFAULT NULL COMMENT '沪股通净买入,元',
  `sgt`               DECIMAL(20,2)          DEFAULT NULL COMMENT '深股通净买入,元',
  `north_money`       DECIMAL(20,2)          DEFAULT NULL COMMENT '北向净买入(hgt+sgt),元',
  `south_money`       DECIMAL(20,2)          DEFAULT NULL COMMENT '南向净买入(ggt_ss+ggt_sz),元',
  `update_time`       DATETIME      NOT NULL          COMMENT '入库时间',
  PRIMARY KEY (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='沪深港通日度净买入,元';
```

> **2024-08 后口径变更:** 港交所只公布交易日净买入总额,**不再公布个股持股快照**。日度总额数据仍可用,但个股北向持仓无法获取。本表仅做总额,不做个股层。

#### E2-S1-T3 龙虎榜营业部明细(akshare)

```sql
-- ====================================================================
-- ods_event_lhb_seat_detail · 龙虎榜营业部买卖明细
-- 数据源: akshare stock_lhb_detail_em(东方财富)
-- 频率: 仅有龙虎榜的交易日, 每日 ~50-200 只股 × 5 买 5 卖 = ~500-2000 行
-- ====================================================================
CREATE TABLE `ods_event_lhb_seat_detail` (
  `id`                BIGINT        NOT NULL AUTO_INCREMENT,
  `trade_date`        DATE          NOT NULL          COMMENT '交易日',
  `ts_code`           VARCHAR(16)   NOT NULL          COMMENT '股票代码',
  `stock_name`        VARCHAR(32)            DEFAULT NULL COMMENT '股票简称',
  `reason`            VARCHAR(128)           DEFAULT NULL COMMENT '上榜原因(如日涨幅 7%)',
  `seat_name`         VARCHAR(128)  NOT NULL          COMMENT '营业部 / 席位名称',
  `side`              ENUM('buy','sell') NOT NULL    COMMENT '买卖方向',
  `rank_in_side`      TINYINT                DEFAULT NULL COMMENT '该方向序号 1-5',
  `buy_amount`        DECIMAL(20,2)          DEFAULT NULL COMMENT '买入金额,元',
  `sell_amount`       DECIMAL(20,2)          DEFAULT NULL COMMENT '卖出金额,元',
  `net_amount`        DECIMAL(20,2)          DEFAULT NULL COMMENT '净额,元',
  `update_time`       DATETIME      NOT NULL          COMMENT '入库时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_date_ts_seat_side` (`trade_date`, `ts_code`, `seat_name`, `side`),
  KEY `idx_seat_date` (`seat_name`, `trade_date`),
  KEY `idx_ts_date`   (`ts_code`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='龙虎榜营业部明细,自增 id 主键, 业务唯一键(date, ts, seat, side)';
```

#### E2-S1-T4 游资席位库(自建维表)

```sql
-- ====================================================================
-- dim_yz_seat · 游资 / 知名席位库
-- 数据源: 手工维护 + 拌入 jcw 等公开排行榜
-- 用途: 龙虎榜识别游资 / 机构 / 散户大单
-- ====================================================================
CREATE TABLE `dim_yz_seat` (
  `seat_id`           VARCHAR(32)   NOT NULL          COMMENT '席位 ID(MD5 of seat_name)',
  `seat_name`         VARCHAR(128)  NOT NULL          COMMENT '席位标准名称',
  `seat_alias`        VARCHAR(500)           DEFAULT NULL COMMENT '别名,逗号分隔(数据源命名差异)',
  `seat_type`         ENUM('hot_money','institution','retail_big','foreign','other')
                                    NOT NULL          COMMENT '席位类型',
  `nickname`          VARCHAR(64)            DEFAULT NULL COMMENT '江湖花名,如「赵老哥」「炒股养家」',
  `style_tag`         VARCHAR(64)            DEFAULT NULL COMMENT '风格标签: 短线/打板/低吸/趋势',
  `is_active`         TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否活跃',
  `note`              TEXT                   DEFAULT NULL COMMENT '备注',
  `update_time`       DATETIME      NOT NULL          COMMENT '更新时间',
  PRIMARY KEY (`seat_id`),
  UNIQUE KEY `uk_seat_name` (`seat_name`),
  KEY `idx_seat_type` (`seat_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='游资席位库, 手工维护';
```

> **冷启动数据来源:** 集思录、jisilu、雪球、东财等公开"营业部排行"。**席位名称匹配难点:** 不同源命名差异大(如「中国银河证券股份有限公司绍兴营业部」 vs 「银河证券绍兴」),`seat_alias` 用于兜底。Antigravity 实施时建议:首批 50-100 个公认游资 + 主要机构席位入库,随后按需扩展。

#### E2-S1-T5 ETF 份额日度(akshare)

```sql
-- ====================================================================
-- ods_etf_share_daily · ETF 份额日度
-- 数据源: akshare fund_etf_fund_info_em
-- 用途: 净申购计算, 国家队信号(中央汇金/证金的 ETF)
-- ====================================================================
CREATE TABLE `ods_etf_share_daily` (
  `trade_date`        DATE          NOT NULL          COMMENT '交易日',
  `ts_code`           VARCHAR(16)   NOT NULL          COMMENT 'ETF 代码',
  `etf_name`          VARCHAR(64)            DEFAULT NULL COMMENT 'ETF 名称',
  `share_total`       DECIMAL(20,4)          DEFAULT NULL COMMENT '总份额,亿份',
  `nav`               DECIMAL(10,4)          DEFAULT NULL COMMENT '单位净值,元',
  `aum`               DECIMAL(20,2)          DEFAULT NULL COMMENT '资产规模,元(派生 = share×nav×1e8)',
  `share_chg`         DECIMAL(20,4)          DEFAULT NULL COMMENT '份额变化,亿份(vs 前日)',
  `net_inflow_est`    DECIMAL(20,2)          DEFAULT NULL COMMENT '估算净申购金额,元(=share_chg×nav×1e8)',
  `is_state_team`     TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否国家队 ETF(中央汇金/证金重仓)',
  `update_time`       DATETIME      NOT NULL          COMMENT '入库时间',
  PRIMARY KEY (`trade_date`, `ts_code`),
  KEY `idx_ts_date` (`ts_code`, `trade_date`),
  KEY `idx_state_team` (`is_state_team`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='ETF 份额日度,亿份,标识国家队 ETF';
```

> **国家队 ETF 识别:** 通过定期公告的「中央汇金 / 中证金融」前十大持有人识别。本字段需手工 / 半自动维护(放在 `fund_basic` 维表,本表只做标识冗余便于查询)。

#### E2-S1-T6 期货合约维表 + 日线

```sql
-- ====================================================================
-- fut_basic · 期货合约维表
-- 数据源: Tushare fut_basic
-- 用途: 识别股指期货主力合约(IF/IH/IC/IM)
-- ====================================================================
CREATE TABLE `fut_basic` (
  `ts_code`           VARCHAR(16)   NOT NULL          COMMENT '合约代码,如 IF2406.CFX',
  `symbol`            VARCHAR(16)            DEFAULT NULL COMMENT '交易代码',
  `exchange`          VARCHAR(8)             DEFAULT NULL COMMENT '交易所',
  `name`              VARCHAR(64)            DEFAULT NULL COMMENT '合约名称',
  `fut_code`          VARCHAR(8)             DEFAULT NULL COMMENT '品种代码: IF/IH/IC/IM',
  `multiplier`        INT                    DEFAULT NULL COMMENT '合约乘数',
  `trade_unit`        VARCHAR(16)            DEFAULT NULL COMMENT '交易单位',
  `list_date`         DATE                   DEFAULT NULL COMMENT '上市日',
  `delist_date`       DATE                   DEFAULT NULL COMMENT '退市日',
  `update_time`       DATETIME      NOT NULL          COMMENT '入库时间',
  PRIMARY KEY (`ts_code`),
  KEY `idx_fut_code` (`fut_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='期货合约维表';

-- ====================================================================
-- ods_fut_daily · 期货合约日线
-- 数据源: Tushare fut_daily
-- 频率: 每个交易日 × 数百活跃合约
-- ====================================================================
CREATE TABLE `ods_fut_daily` (
  `trade_date`        DATE          NOT NULL          COMMENT '交易日',
  `ts_code`           VARCHAR(16)   NOT NULL          COMMENT '合约代码',
  `pre_close`         DECIMAL(16,4)          DEFAULT NULL COMMENT '前收',
  `open`              DECIMAL(16,4)          DEFAULT NULL COMMENT '开盘',
  `high`              DECIMAL(16,4)          DEFAULT NULL COMMENT '最高',
  `low`               DECIMAL(16,4)          DEFAULT NULL COMMENT '最低',
  `close`             DECIMAL(16,4)          DEFAULT NULL COMMENT '收盘',
  `settle`            DECIMAL(16,4)          DEFAULT NULL COMMENT '结算价',
  `vol`               BIGINT                 DEFAULT NULL COMMENT '成交量,手',
  `amount`            DECIMAL(20,2)          DEFAULT NULL COMMENT '成交额,元',
  `oi`                BIGINT                 DEFAULT NULL COMMENT '持仓量,手',
  `oi_chg`            BIGINT                 DEFAULT NULL COMMENT '持仓量变化',
  `update_time`       DATETIME      NOT NULL          COMMENT '入库时间',
  PRIMARY KEY (`trade_date`, `ts_code`),
  KEY `idx_ts_date` (`ts_code`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='期货日线';
```

#### E2-S1-T7 L3 资金流向主表

```sql
-- ====================================================================
-- ads_l3_capital_flow · L3 资金合成日度
-- 频率: 每个交易日 1 行
-- ====================================================================
CREATE TABLE `ads_l3_capital_flow` (
  `trade_date`              DATE         NOT NULL            COMMENT '交易日',

  -- ===== 主力资金 =====
  `mainforce_net_amount`    DECIMAL(20,2)         DEFAULT NULL COMMENT '主力净流入合计,元',
  `mainforce_buy_count`     INT                   DEFAULT NULL COMMENT '主力净流入家数',
  `mainforce_sell_count`    INT                   DEFAULT NULL COMMENT '主力净流出家数',
  `elg_net_amount`          DECIMAL(20,2)         DEFAULT NULL COMMENT '超大单净流入,元',
  `lg_net_amount`           DECIMAL(20,2)         DEFAULT NULL COMMENT '大单净流入,元',
  `mid_net_amount`          DECIMAL(20,2)         DEFAULT NULL COMMENT '中单净流入,元',
  `sm_net_amount`           DECIMAL(20,2)         DEFAULT NULL COMMENT '小单净流入,元',

  -- ===== 北向 =====
  `north_money`             DECIMAL(20,2)         DEFAULT NULL COMMENT '北向净买入,元(2024-08 后仅总额)',
  `north_money_5d`          DECIMAL(20,2)         DEFAULT NULL COMMENT '北向 5 日累计,元',
  `north_money_20d`         DECIMAL(20,2)         DEFAULT NULL COMMENT '北向 20 日累计,元',

  -- ===== 两融 =====
  `margin_balance`          DECIMAL(20,2)         DEFAULT NULL COMMENT '融资余额,元',
  `margin_balance_chg`      DECIMAL(20,2)         DEFAULT NULL COMMENT '融资余额日变化,元',
  `short_balance`           DECIMAL(20,2)         DEFAULT NULL COMMENT '融券余额,元',
  `margin_buy_amount`       DECIMAL(20,2)         DEFAULT NULL COMMENT '当日融资买入额,元',

  -- ===== ETF =====
  `etf_net_inflow_total`    DECIMAL(20,2)         DEFAULT NULL COMMENT 'ETF 净申购合计,元',
  `etf_net_inflow_state`    DECIMAL(20,2)         DEFAULT NULL COMMENT '国家队 ETF 净申购,元',
  `etf_net_inflow_equity`   DECIMAL(20,2)         DEFAULT NULL COMMENT '股票 ETF 净申购,元',

  -- ===== 龙虎榜 =====
  `lhb_count`               INT                   DEFAULT NULL COMMENT '上榜家数',
  `lhb_buy_total`           DECIMAL(20,2)         DEFAULT NULL COMMENT '龙虎榜买入合计,元',
  `lhb_sell_total`          DECIMAL(20,2)         DEFAULT NULL COMMENT '龙虎榜卖出合计,元',
  `lhb_net_total`           DECIMAL(20,2)         DEFAULT NULL COMMENT '龙虎榜净买入,元',
  `lhb_yz_buy`              DECIMAL(20,2)         DEFAULT NULL COMMENT '游资买入,元',
  `lhb_yz_sell`             DECIMAL(20,2)         DEFAULT NULL COMMENT '游资卖出,元',
  `lhb_inst_buy`            DECIMAL(20,2)         DEFAULT NULL COMMENT '机构买入,元',
  `lhb_inst_sell`           DECIMAL(20,2)         DEFAULT NULL COMMENT '机构卖出,元',

  -- ===== 大宗 =====
  `block_trade_amount`      DECIMAL(20,2)         DEFAULT NULL COMMENT '大宗交易合计,元',
  `block_trade_premium_avg` DECIMAL(10,6)         DEFAULT NULL COMMENT '大宗加权平均溢价率,小数',

  -- ===== 期指基差(主力合约) =====
  `if_basis`                DECIMAL(16,4)         DEFAULT NULL COMMENT 'IF 主力基差(收 - 现货 000300)',
  `ih_basis`                DECIMAL(16,4)         DEFAULT NULL COMMENT 'IH 主力基差(收 - 现货 000016)',
  `ic_basis`                DECIMAL(16,4)         DEFAULT NULL COMMENT 'IC 主力基差(收 - 现货 000905)',
  `im_basis`                DECIMAL(16,4)         DEFAULT NULL COMMENT 'IM 主力基差(收 - 现货 000852)',
  `if_basis_pct`            DECIMAL(10,6)         DEFAULT NULL COMMENT 'IF 基差年化贴水率,小数',

  -- ===== 综合 =====
  `capital_score`           DECIMAL(6,2)          DEFAULT NULL COMMENT '资金综合评分 0-100',
  `capital_label`           VARCHAR(16)           DEFAULT NULL COMMENT '资金标签: 流出/谨慎/中性/流入/抢筹',

  `update_time`             DATETIME     NOT NULL            COMMENT '入库时间',
  PRIMARY KEY (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='L3 资金合成日度';
```

#### E2-S1-T8 龙虎榜个股流水(供前端列表展示)

```sql
-- ====================================================================
-- ads_l3_lhb_stock · 龙虎榜个股汇总(每日 N 行,N=上榜数)
-- 来源: ods_event_lhb_seat_detail 聚合
-- 用途: 前端龙虎榜 TOP 10 列表
-- ====================================================================
CREATE TABLE `ads_l3_lhb_stock` (
  `trade_date`        DATE          NOT NULL          COMMENT '交易日',
  `ts_code`           VARCHAR(16)   NOT NULL          COMMENT '股票代码',
  `stock_name`        VARCHAR(32)            DEFAULT NULL COMMENT '股票简称',
  `industry`          VARCHAR(32)            DEFAULT NULL COMMENT '申万一级',
  `concept_top1`      VARCHAR(64)            DEFAULT NULL COMMENT '所属热门概念(最热 1 个)',
  `pct_chg`           DECIMAL(10,6)          DEFAULT NULL COMMENT '当日涨跌幅,小数',
  `turnover_rate`     DECIMAL(10,6)          DEFAULT NULL COMMENT '换手率,小数',

  `lhb_buy`           DECIMAL(20,2)          DEFAULT NULL COMMENT '买入合计,元',
  `lhb_sell`          DECIMAL(20,2)          DEFAULT NULL COMMENT '卖出合计,元',
  `lhb_net`           DECIMAL(20,2)          DEFAULT NULL COMMENT '净买入,元',

  `yz_buy_count`      TINYINT                DEFAULT NULL COMMENT '游资买席数(标注游资上榜次数)',
  `yz_sell_count`     TINYINT                DEFAULT NULL COMMENT '游资卖席数',
  `inst_buy_count`    TINYINT                DEFAULT NULL COMMENT '机构买席数',
  `inst_sell_count`   TINYINT                DEFAULT NULL COMMENT '机构卖席数',

  `top_yz_seat`       VARCHAR(128)           DEFAULT NULL COMMENT '最大买入游资昵称(如赵老哥)',
  `lhb_reason`        VARCHAR(128)           DEFAULT NULL COMMENT '上榜原因',
  `update_time`       DATETIME      NOT NULL          COMMENT '入库时间',
  PRIMARY KEY (`trade_date`, `ts_code`),
  KEY `idx_lhb_net` (`trade_date`, `lhb_net`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='龙虎榜个股汇总';
```

#### E2-S1-T*-AC 验收标准

> **Given** 7 张新表创建语句
> **When** 全部 DDL 执行
> **Then** `INFORMATION_SCHEMA` 中 7 张表全部存在,且 ENUM/外键/UNIQUE 约束生效

> **Given** `ods_event_lhb_seat_detail` 同日重复写入相同 `(date, ts, seat, side)`
> **When** 第二次 INSERT
> **Then** 因 `uk_date_ts_seat_side` 报错或 ON DUPLICATE KEY 触发更新,**不出现重复数据**

---

### E2-S2 计算 SQL

#### E2-S2-T1 主力资金聚合

```sql
SET @td := '2026-04-27';

INSERT INTO ads_l3_capital_flow (
  trade_date,
  mainforce_net_amount, mainforce_buy_count, mainforce_sell_count,
  elg_net_amount, lg_net_amount, mid_net_amount, sm_net_amount,
  update_time
)
SELECT
  @td,
  SUM(net_mf_amount)                                                AS mainforce_net,
  SUM(CASE WHEN net_mf_amount > 0 THEN 1 ELSE 0 END)                AS buy_cnt,
  SUM(CASE WHEN net_mf_amount < 0 THEN 1 ELSE 0 END)                AS sell_cnt,
  SUM(COALESCE(buy_elg_amount, 0) - COALESCE(sell_elg_amount, 0))   AS elg_net,
  SUM(COALESCE(buy_lg_amount, 0)  - COALESCE(sell_lg_amount, 0))    AS lg_net,
  SUM(COALESCE(buy_md_amount, 0)  - COALESCE(sell_md_amount, 0))    AS mid_net,
  SUM(COALESCE(buy_sm_amount, 0)  - COALESCE(sell_sm_amount, 0))    AS sm_net,
  NOW()
FROM ods_moneyflow_stock
WHERE trade_date = @td
ON DUPLICATE KEY UPDATE
  mainforce_net_amount = VALUES(mainforce_net_amount),
  mainforce_buy_count  = VALUES(mainforce_buy_count),
  mainforce_sell_count = VALUES(mainforce_sell_count),
  elg_net_amount       = VALUES(elg_net_amount),
  lg_net_amount        = VALUES(lg_net_amount),
  mid_net_amount       = VALUES(mid_net_amount),
  sm_net_amount        = VALUES(sm_net_amount),
  update_time          = NOW();
```

#### E2-S2-T2 北向(总额 + 滚动累计)

```sql
UPDATE ads_l3_capital_flow a
JOIN (
  SELECT
    @td AS trade_date,
    h.north_money,
    -- 5 日累计
    (SELECT SUM(h2.north_money) FROM ods_moneyflow_hsgt h2
     WHERE h2.trade_date BETWEEN
       (SELECT cal_date FROM trade_cal
        WHERE cal_date <= @td AND is_open=1
        ORDER BY cal_date DESC LIMIT 4,1)
       AND @td) AS n5,
    -- 20 日累计
    (SELECT SUM(h2.north_money) FROM ods_moneyflow_hsgt h2
     WHERE h2.trade_date BETWEEN
       (SELECT cal_date FROM trade_cal
        WHERE cal_date <= @td AND is_open=1
        ORDER BY cal_date DESC LIMIT 19,1)
       AND @td) AS n20
  FROM ods_moneyflow_hsgt h
  WHERE h.trade_date = @td
) n ON n.trade_date = a.trade_date
SET a.north_money     = n.north_money,
    a.north_money_5d  = n.n5,
    a.north_money_20d = n.n20;
```

#### E2-S2-T3 两融汇总

```sql
-- 沿用 market_margin_summary
UPDATE ads_l3_capital_flow a
JOIN (
  SELECT
    m.trade_date,
    m.rzye  AS bal,
    m.rzye - LAG_VALUE.prev_bal AS bal_chg,
    m.rqye  AS short_bal,
    m.rzmre AS buy_amt
  FROM market_margin_summary m
  CROSS JOIN (
    SELECT m2.rzye AS prev_bal
    FROM market_margin_summary m2
    WHERE m2.trade_date < @td
    ORDER BY m2.trade_date DESC LIMIT 1
  ) LAG_VALUE
  WHERE m.trade_date = @td
) mg ON mg.trade_date = a.trade_date
SET a.margin_balance      = mg.bal,
    a.margin_balance_chg  = mg.bal_chg,
    a.short_balance       = mg.short_bal,
    a.margin_buy_amount   = mg.buy_amt;
```

> **TBD:** `market_margin_summary` 字段名 `rzye/rqye/rzmre` 与 Tushare 一致(融资余额/融券余额/融资买入额),但**单位需 Antigravity 确认**。Tushare 默认元为单位,本表沿用元。若发现单位为亿元需统一换算。

#### E2-S2-T4 ETF 净申购

```sql
UPDATE ads_l3_capital_flow a
JOIN (
  SELECT
    @td AS trade_date,
    SUM(net_inflow_est)                                              AS total,
    SUM(CASE WHEN is_state_team = 1 THEN net_inflow_est ELSE 0 END)  AS state_team,
    -- 股票 ETF: 排除货币、债券、商品(代码段判断, TBD 完整规则)
    SUM(CASE WHEN ts_code LIKE '5%' OR ts_code LIKE '159%' THEN net_inflow_est ELSE 0 END)
                                                                     AS equity
  FROM ods_etf_share_daily
  WHERE trade_date = @td AND net_inflow_est IS NOT NULL
) e ON e.trade_date = a.trade_date
SET a.etf_net_inflow_total  = e.total,
    a.etf_net_inflow_state  = e.state_team,
    a.etf_net_inflow_equity = e.equity;
```

> **简化口径:** 「股票 ETF」用代码段宽口径(5xx + 159xxx 含债券、跨境、商品),**实际应 JOIN `fund_basic.fund_type` 严格筛**。本期为简化先用代码段,前端展示需注明。

#### E2-S2-T5 龙虎榜聚合(总览 + 个股)

```sql
-- 总览
UPDATE ads_l3_capital_flow a
JOIN (
  SELECT
    @td AS trade_date,
    COUNT(DISTINCT s.ts_code)                              AS lhb_cnt,
    SUM(CASE WHEN s.side = 'buy'  THEN s.buy_amount ELSE 0 END)  AS buy_t,
    SUM(CASE WHEN s.side = 'sell' THEN s.sell_amount ELSE 0 END) AS sell_t,
    SUM(CASE WHEN s.side = 'buy'  THEN s.buy_amount ELSE 0 END)
      - SUM(CASE WHEN s.side = 'sell' THEN s.sell_amount ELSE 0 END) AS net_t,
    -- 游资席位识别
    SUM(CASE WHEN s.side = 'buy'  AND y.seat_type = 'hot_money'
             THEN s.buy_amount ELSE 0 END) AS yz_b,
    SUM(CASE WHEN s.side = 'sell' AND y.seat_type = 'hot_money'
             THEN s.sell_amount ELSE 0 END) AS yz_s,
    SUM(CASE WHEN s.side = 'buy'  AND y.seat_type = 'institution'
             THEN s.buy_amount ELSE 0 END) AS in_b,
    SUM(CASE WHEN s.side = 'sell' AND y.seat_type = 'institution'
             THEN s.sell_amount ELSE 0 END) AS in_s
  FROM ods_event_lhb_seat_detail s
  LEFT JOIN dim_yz_seat y
    ON y.seat_name = s.seat_name
    OR FIND_IN_SET(s.seat_name, REPLACE(y.seat_alias, ',', ',')) > 0
  WHERE s.trade_date = @td
) l ON l.trade_date = a.trade_date
SET a.lhb_count      = l.lhb_cnt,
    a.lhb_buy_total  = l.buy_t,
    a.lhb_sell_total = l.sell_t,
    a.lhb_net_total  = l.net_t,
    a.lhb_yz_buy     = l.yz_b,
    a.lhb_yz_sell    = l.yz_s,
    a.lhb_inst_buy   = l.in_b,
    a.lhb_inst_sell  = l.in_s;
```

```sql
-- 个股(每只上榜票 1 行)
INSERT INTO ads_l3_lhb_stock (
  trade_date, ts_code, stock_name, industry,
  pct_chg, turnover_rate,
  lhb_buy, lhb_sell, lhb_net,
  yz_buy_count, yz_sell_count, inst_buy_count, inst_sell_count,
  top_yz_seat, lhb_reason,
  update_time
)
SELECT
  s.trade_date,
  s.ts_code,
  MAX(s.stock_name),
  MAX(sw.industry_name),
  MAX(k.pct_chg),
  MAX(db.turnover_rate / 100),  -- daily_basic 的 turnover_rate 是百分比
  SUM(CASE WHEN s.side='buy'  THEN s.buy_amount  ELSE 0 END),
  SUM(CASE WHEN s.side='sell' THEN s.sell_amount ELSE 0 END),
  SUM(CASE WHEN s.side='buy'  THEN s.buy_amount  ELSE 0 END)
    - SUM(CASE WHEN s.side='sell' THEN s.sell_amount ELSE 0 END),
  SUM(CASE WHEN s.side='buy'  AND y.seat_type='hot_money'   THEN 1 ELSE 0 END),
  SUM(CASE WHEN s.side='sell' AND y.seat_type='hot_money'   THEN 1 ELSE 0 END),
  SUM(CASE WHEN s.side='buy'  AND y.seat_type='institution' THEN 1 ELSE 0 END),
  SUM(CASE WHEN s.side='sell' AND y.seat_type='institution' THEN 1 ELSE 0 END),
  -- 最大买入游资(子查询)
  (SELECT y2.nickname FROM ods_event_lhb_seat_detail s2
   LEFT JOIN dim_yz_seat y2 ON y2.seat_name = s2.seat_name
   WHERE s2.trade_date = s.trade_date AND s2.ts_code = s.ts_code
     AND s2.side = 'buy' AND y2.seat_type = 'hot_money'
   ORDER BY s2.buy_amount DESC LIMIT 1),
  MAX(s.reason),
  NOW()
FROM ods_event_lhb_seat_detail s
LEFT JOIN dim_yz_seat y ON y.seat_name = s.seat_name
LEFT JOIN stock_industry_sw sw ON sw.code = SUBSTRING(s.ts_code, 1, 6)
LEFT JOIN stock_kline_daily k
  ON k.code = SUBSTRING(s.ts_code, 1, 6) AND k.trade_date = s.trade_date
LEFT JOIN daily_basic db
  ON db.ts_code = s.ts_code AND db.trade_date = s.trade_date
WHERE s.trade_date = @td
GROUP BY s.trade_date, s.ts_code
ON DUPLICATE KEY UPDATE
  lhb_buy = VALUES(lhb_buy), lhb_sell = VALUES(lhb_sell),
  lhb_net = VALUES(lhb_net), update_time = NOW();
```

#### E2-S2-T6 大宗交易聚合

```sql
UPDATE ads_l3_capital_flow a
JOIN (
  SELECT
    @td AS trade_date,
    SUM(amount * 10000) AS bt_amt,  -- stock_block_trade.amount 是万元, 转元
    -- 加权平均溢价率: (price - close) / close 用成交额加权
    SUM(((price - close_price) / close_price) * amount)
      / NULLIF(SUM(amount), 0) AS premium_avg
  FROM stock_block_trade
  WHERE trade_date = @td AND close_price > 0
) bt ON bt.trade_date = a.trade_date
SET a.block_trade_amount      = bt.bt_amt,
    a.block_trade_premium_avg = bt.premium_avg;
```

> **TBD:** `stock_block_trade` 字段名(`amount`/`price`/`close_price`)需 Antigravity 实测确认。

#### E2-S2-T7 期指基差

```sql
-- IF/IH/IC/IM 主力合约: 当日成交量最大者
-- 现货指数 close 来自 ods_index_daily

UPDATE ads_l3_capital_flow a
JOIN (
  SELECT
    @td AS trade_date,
    MAX(CASE WHEN cal.fut_code = 'IF' THEN cal.fut_close - cal.idx_close END) AS if_b,
    MAX(CASE WHEN cal.fut_code = 'IH' THEN cal.fut_close - cal.idx_close END) AS ih_b,
    MAX(CASE WHEN cal.fut_code = 'IC' THEN cal.fut_close - cal.idx_close END) AS ic_b,
    MAX(CASE WHEN cal.fut_code = 'IM' THEN cal.fut_close - cal.idx_close END) AS im_b
  FROM (
    -- 计算每个品种的主力合约基差
    SELECT
      fb.fut_code,
      f.close   AS fut_close,
      idx.close AS idx_close,
      f.vol,
      @rk := IF(@cur = fb.fut_code, @rk+1, 1) AS rk,
      @cur := fb.fut_code
    FROM ods_fut_daily f
    JOIN fut_basic fb ON fb.ts_code = f.ts_code
    JOIN ods_index_daily idx
      ON idx.ts_code = CASE fb.fut_code
                         WHEN 'IF' THEN '000300.SH'
                         WHEN 'IH' THEN '000016.SH'
                         WHEN 'IC' THEN '000905.SH'
                         WHEN 'IM' THEN '000852.SH'
                       END
     AND idx.trade_date = f.trade_date
    CROSS JOIN (SELECT @rk:=0, @cur:='') v
    WHERE f.trade_date = @td
      AND fb.fut_code IN ('IF','IH','IC','IM')
    ORDER BY fb.fut_code, f.vol DESC
  ) cal
  WHERE cal.rk = 1
) b ON b.trade_date = a.trade_date
SET a.if_basis = b.if_b,
    a.ih_basis = b.ih_b,
    a.ic_basis = b.ic_b,
    a.im_basis = b.im_b;
```

> **MySQL 5.7 注意:** 上述变量赋值依赖 ORDER BY 在子查询中生效。MySQL 5.7 默认仍可用,但 8.0 后需要外层 SELECT 写法。**实施时建议分两步**:先单独按 `fut_code` 分组取 max(vol) 合约,再 JOIN 取 close,可读性更高。

#### E2-S2-T8 综合评分

```sql
-- 资金综合评分: 主力 30 / 北向 25 / 两融 15 / ETF 15 / 龙虎榜游资 15
UPDATE ads_l3_capital_flow a
SET
  a.capital_score = ROUND(
      LEAST(100, GREATEST(0, (COALESCE(a.mainforce_net_amount,0)/1e10 + 5) / 10 * 100)) * 0.30
    + LEAST(100, GREATEST(0, (COALESCE(a.north_money,0)/1e9 + 5) / 10 * 100)) * 0.25
    + LEAST(100, GREATEST(0, (COALESCE(a.margin_balance_chg,0)/1e9 + 3) / 6 * 100)) * 0.15
    + LEAST(100, GREATEST(0, (COALESCE(a.etf_net_inflow_total,0)/1e9 + 3) / 6 * 100)) * 0.15
    + LEAST(100, GREATEST(0, (COALESCE(a.lhb_yz_buy,0) - COALESCE(a.lhb_yz_sell,0))/1e9 + 1) / 2 * 100) * 0.15
  , 2),
  a.capital_label = CASE
    WHEN a.capital_score >= 80 THEN '抢筹'
    WHEN a.capital_score >= 60 THEN '流入'
    WHEN a.capital_score >= 40 THEN '中性'
    WHEN a.capital_score >= 20 THEN '谨慎'
    ELSE '流出'
  END
WHERE a.trade_date = @td;
```

> **量纲说明:** 主力净流入分母 100 亿(/1e10)中位数,北向 / ETF / 两融用 10 亿(/1e9)。**首次落地后需要 1 周观察分布,再调归一化分母**。

#### E2-S2-T*-AC 验收标准

> **Given** ods_moneyflow_stock 同日有 5400 行
> **When** 执行 E2-S2-T1
> **Then** ads_l3_capital_flow 该日 1 行,`mainforce_buy_count + mainforce_sell_count + (净额=0 数) = 5400`

> **Given** 龙虎榜某日 50 只票上榜
> **When** 执行 E2-S2-T5
> **Then** `ads_l3_lhb_stock` 该日 50 行,`ads_l3_capital_flow.lhb_count = 50`,且 `lhb_buy_total - lhb_sell_total = lhb_net_total`

---

### E2-S3 微信小程序前端

**作为** 用户,**我希望** 在资金页一屏看到主力 / 北向 / 两融 / ETF / 龙虎榜五大资金信号,**以便** 验证情绪页的高低判断。

#### E2-S3-T1 wxml 主体

```xml
<!-- pages/capital/capital.wxml -->
<view class="page-wrap">

  <!-- 顶部综合 -->
  <view class="hero">
    <view class="hero-side-bar"></view>
    <view class="hero-meta">
      <text class="hero-date mono">{{trade_date}}</text>
      <text class="hero-cn">资金合成</text>
    </view>
    <view class="hero-score">
      <text class="score-num mono">{{capital_score}}</text>
      <text class="score-label">{{capital_label}}</text>
    </view>
  </view>

  <!-- 主力资金 -->
  <view class="card">
    <view class="card-side-bar"></view>
    <view class="card-header">
      <text class="card-title-cn">主力资金</text>
      <text class="card-title-en">SMART MONEY</text>
    </view>
    <view class="big-num-row">
      <text class="big-num mono {{mainforce_net_amount >= 0 ? 'up' : 'down'}}">
        {{mainforce_net_amount >= 0 ? '+' : ''}}{{mainforce_net_amount_yi}}
      </text>
      <text class="big-unit">亿</text>
    </view>
    <view class="sub-grid-4">
      <view class="kv">
        <text class="kv-k">超大单</text>
        <text class="kv-v mono {{elg_net_amount >= 0 ? 'up' : 'down'}}">{{elg_net_amount_yi}}亿</text>
      </view>
      <view class="kv">
        <text class="kv-k">大单</text>
        <text class="kv-v mono {{lg_net_amount >= 0 ? 'up' : 'down'}}">{{lg_net_amount_yi}}亿</text>
      </view>
      <view class="kv">
        <text class="kv-k">流入家数</text>
        <text class="kv-v mono up">{{mainforce_buy_count}}</text>
      </view>
      <view class="kv">
        <text class="kv-k">流出家数</text>
        <text class="kv-v mono down">{{mainforce_sell_count}}</text>
      </view>
    </view>
  </view>

  <!-- 北向 + 两融 双卡 -->
  <view class="dual-grid">
    <view class="card-half">
      <view class="card-side-bar"></view>
      <view class="card-header">
        <text class="card-title-cn">北向资金</text>
        <text class="card-title-en">NORTH</text>
      </view>
      <text class="dual-big mono {{north_money >= 0 ? 'up' : 'down'}}">
        {{north_money >= 0 ? '+' : ''}}{{north_money_yi}}亿
      </text>
      <view class="dual-detail">
        <view class="kv"><text class="kv-k">5 日</text><text class="kv-v mono">{{north_money_5d_yi}}亿</text></view>
        <view class="kv"><text class="kv-k">20 日</text><text class="kv-v mono">{{north_money_20d_yi}}亿</text></view>
      </view>
      <text class="card-note">2024-08 后仅披露日度总额</text>
    </view>

    <view class="card-half">
      <view class="card-side-bar"></view>
      <view class="card-header">
        <text class="card-title-cn">两融余额</text>
        <text class="card-title-en">MARGIN</text>
      </view>
      <text class="dual-big mono">{{margin_balance_yi}}亿</text>
      <view class="dual-detail">
        <view class="kv">
          <text class="kv-k">日变化</text>
          <text class="kv-v mono {{margin_balance_chg >= 0 ? 'up' : 'down'}}">
            {{margin_balance_chg >= 0 ? '+' : ''}}{{margin_balance_chg_yi}}亿
          </text>
        </view>
        <view class="kv"><text class="kv-k">融资买入</text><text class="kv-v mono">{{margin_buy_amount_yi}}亿</text></view>
      </view>
    </view>
  </view>

  <!-- ETF 净申购 -->
  <view class="card">
    <view class="card-side-bar"></view>
    <view class="card-header">
      <text class="card-title-cn">ETF 资金</text>
      <text class="card-title-en">ETF FLOW</text>
    </view>
    <view class="etf-row">
      <view class="etf-cell main">
        <text class="etf-cn">合计净申购</text>
        <text class="etf-num mono {{etf_net_inflow_total >= 0 ? 'up' : 'down'}}">
          {{etf_net_inflow_total_yi}}亿
        </text>
      </view>
      <view class="etf-cell">
        <text class="etf-cn">国家队 ETF</text>
        <text class="etf-num mono {{etf_net_inflow_state >= 0 ? 'up' : 'down'}}">
          {{etf_net_inflow_state_yi}}亿
        </text>
      </view>
      <view class="etf-cell">
        <text class="etf-cn">股票 ETF</text>
        <text class="etf-num mono {{etf_net_inflow_equity >= 0 ? 'up' : 'down'}}">
          {{etf_net_inflow_equity_yi}}亿
        </text>
      </view>
    </view>
  </view>

  <!-- 龙虎榜 -->
  <view class="card">
    <view class="card-side-bar"></view>
    <view class="card-header">
      <text class="card-title-cn">龙虎榜</text>
      <text class="card-title-en">LHB · {{lhb_count}}</text>
    </view>
    <view class="lhb-summary">
      <view class="kv"><text class="kv-k">买入</text><text class="kv-v mono up">{{lhb_buy_total_yi}}亿</text></view>
      <view class="kv"><text class="kv-k">卖出</text><text class="kv-v mono down">{{lhb_sell_total_yi}}亿</text></view>
      <view class="kv"><text class="kv-k">游资净买</text><text class="kv-v mono">{{lhb_yz_net_yi}}亿</text></view>
    </view>
    <view class="lhb-list">
      <view class="lhb-row" wx:for="{{lhb_top10}}" wx:key="ts_code">
        <view class="lhb-name">
          <text class="lhb-stock">{{item.stock_name}}</text>
          <text class="lhb-tag mono" wx:if="{{item.top_yz_seat}}">{{item.top_yz_seat}}</text>
        </view>
        <view class="lhb-meta">
          <text class="mono {{item.pct_chg >= 0 ? 'up' : 'down'}}">{{item.pct_chg_pct}}%</text>
          <text class="mono lhb-net {{item.lhb_net >= 0 ? 'up' : 'down'}}">
            {{item.lhb_net >= 0 ? '+' : ''}}{{item.lhb_net_yi}}亿
          </text>
        </view>
      </view>
    </view>
  </view>

  <!-- 期指基差 -->
  <view class="card">
    <view class="card-side-bar"></view>
    <view class="card-header">
      <text class="card-title-cn">期指基差</text>
      <text class="card-title-en">FUTURES BASIS</text>
    </view>
    <view class="basis-grid">
      <view class="basis-cell">
        <text class="basis-cn">IF · 沪深300</text>
        <text class="basis-num mono {{if_basis >= 0 ? 'up' : 'down'}}">{{if_basis}}</text>
      </view>
      <view class="basis-cell">
        <text class="basis-cn">IH · 上证50</text>
        <text class="basis-num mono {{ih_basis >= 0 ? 'up' : 'down'}}">{{ih_basis}}</text>
      </view>
      <view class="basis-cell">
        <text class="basis-cn">IC · 中证500</text>
        <text class="basis-num mono {{ic_basis >= 0 ? 'up' : 'down'}}">{{ic_basis}}</text>
      </view>
      <view class="basis-cell">
        <text class="basis-cn">IM · 中证1000</text>
        <text class="basis-num mono {{im_basis >= 0 ? 'up' : 'down'}}">{{im_basis}}</text>
      </view>
    </view>
    <text class="card-note">基差 = 主力合约收盘 − 现货指数 · 负值贴水</text>
  </view>

  <!-- 大宗交易 -->
  <view class="card">
    <view class="card-side-bar"></view>
    <view class="card-header">
      <text class="card-title-cn">大宗交易</text>
      <text class="card-title-en">BLOCK TRADE</text>
    </view>
    <view class="block-row">
      <view class="block-cell">
        <text class="block-cn">成交合计</text>
        <text class="block-num mono">{{block_trade_amount_yi}}亿</text>
      </view>
      <view class="block-cell">
        <text class="block-cn">加权溢价率</text>
        <text class="block-num mono {{block_trade_premium_avg >= 0 ? 'up' : 'down'}}">
          {{block_trade_premium_avg_pct}}%
        </text>
      </view>
    </view>
  </view>

</view>
```

#### E2-S3-T2 wxss 增量(沿用 sentiment 主样式)

```css
/* pages/capital/capital.wxss · 仅写差异部分 */

.big-num-row {
  display: flex; align-items: baseline; gap: 12rpx;
  padding: 16rpx 0; border-bottom: 1rpx solid var(--hair);
}
.big-num { font-size: 80rpx; font-weight: 700; line-height: 1; }
.big-unit { font-size: 32rpx; color: var(--ink-mute); }

.sub-grid-4 {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 16rpx; padding-top: 24rpx;
}

/* 双卡布局 */
.dual-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 16rpx; margin-bottom: 16rpx;
}
.card-half {
  position: relative; background: var(--bg-card);
  padding: 24rpx 24rpx 24rpx 32rpx; border-radius: 4rpx;
}
.dual-big {
  display: block; font-size: 48rpx; font-weight: 700;
  margin: 16rpx 0; line-height: 1.1;
}
.dual-detail { display: flex; flex-direction: column; gap: 12rpx; }
.card-note {
  display: block; margin-top: 16rpx; padding-top: 12rpx;
  border-top: 1rpx solid var(--hair);
  color: var(--ink-mute); font-size: 22rpx;
}

/* ETF */
.etf-row { display: flex; gap: 1rpx; background: var(--hair); }
.etf-cell {
  flex: 1; background: var(--bg-card); padding: 24rpx 16rpx;
  display: flex; flex-direction: column; gap: 8rpx; align-items: center;
}
.etf-cell.main .etf-num { font-size: 44rpx; font-weight: 700; }
.etf-cn { color: var(--ink-dim); font-size: var(--fs-aux); }
.etf-num { font-size: 36rpx; }

/* 龙虎榜 */
.lhb-summary {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 16rpx; padding-bottom: 16rpx; border-bottom: 1rpx solid var(--hair);
}
.lhb-list { padding-top: 16rpx; }
.lhb-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16rpx 0; border-bottom: 1rpx solid var(--hair);
}
.lhb-row:last-child { border-bottom: none; }
.lhb-name { display: flex; flex-direction: column; gap: 4rpx; }
.lhb-stock { color: var(--ink); font-size: var(--fs-data); }
.lhb-tag {
  color: var(--amber); font-size: 22rpx;
  padding: 2rpx 8rpx; border: 1rpx solid var(--amber); border-radius: 2rpx;
  align-self: flex-start;
}
.lhb-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 4rpx; }
.lhb-net { font-size: var(--fs-data); font-weight: 600; }

/* 期指基差 */
.basis-grid {
  display: grid; grid-template-columns: repeat(2, 1fr);
  gap: 1rpx; background: var(--hair);
}
.basis-cell {
  background: var(--bg-card); padding: 24rpx;
  display: flex; flex-direction: column; gap: 8rpx;
}
.basis-cn { color: var(--ink-dim); font-size: var(--fs-aux); }
.basis-num { font-size: 44rpx; font-weight: 600; }

/* 大宗 */
.block-row { display: flex; gap: 1rpx; background: var(--hair); }
.block-cell {
  flex: 1; background: var(--bg-card); padding: 24rpx;
  display: flex; flex-direction: column; gap: 8rpx;
}
.block-cn { color: var(--ink-dim); font-size: var(--fs-aux); }
.block-num { font-size: 36rpx; font-weight: 600; color: var(--ink); }
```

#### E2-S3-T3 数据接口契约

```yaml
# 接口: GET /api/capital/daily?trade_date=2026-04-27
response:
  code: 0
  data:
    trade_date: "2026-04-27"
    capital_score: 65.20
    capital_label: "流入"

    # 主力
    mainforce_net_amount: 12500000000     # 原始, 元
    mainforce_net_amount_yi: 125.00       # 亿元(后端预转)
    elg_net_amount_yi: 80.50
    lg_net_amount_yi: 44.50
    mainforce_buy_count: 2850
    mainforce_sell_count: 2450

    # 北向
    north_money: -1500000000
    north_money_yi: -15.00
    north_money_5d_yi: -80.50
    north_money_20d_yi: 120.30

    # 两融
    margin_balance_yi: 17580.20
    margin_balance_chg_yi: 12.50
    margin_buy_amount_yi: 1850.00

    # ETF
    etf_net_inflow_total_yi: 35.50
    etf_net_inflow_state_yi: 22.00
    etf_net_inflow_equity_yi: 28.50

    # 龙虎榜
    lhb_count: 38
    lhb_buy_total_yi: 85.30
    lhb_sell_total_yi: 62.50
    lhb_yz_net_yi: 12.80
    lhb_top10:
      - ts_code: "002174.SZ"
        stock_name: "游族网络"
        pct_chg_pct: 9.98
        lhb_net_yi: 2.85
        top_yz_seat: "赵老哥"
      - ts_code: "300663.SZ"
        stock_name: "科蓝软件"
        pct_chg_pct: 20.00
        lhb_net_yi: 1.95
        top_yz_seat: "炒股养家"
      # ... 共 10 条

    # 期指
    if_basis: -28.50
    ih_basis: -12.00
    ic_basis: -65.30
    im_basis: -120.50

    # 大宗
    block_trade_amount_yi: 38.50
    block_trade_premium_avg: -0.0285
    block_trade_premium_avg_pct: -2.85
```

> **单位双轨制:** 后端原始字段保留(用于前端比较判定),`_yi` / `_pct` 转换字段供展示直接使用。这样前端零计算,但接口字段数翻倍,**接受此 trade-off**。

---

### E2-S4 数据字典片段

#### `ods_moneyflow_stock` 关键字段

| 字段 | 类型 | 单位 | 口径 |
|---|---|---|---|
| net_mf_amount | DECIMAL(20,2) | 元 | 主力净流入 = 超大+大单净额(Tushare 原值千元/万元 入库需 ×1000 / ×10000) |
| buy_elg_amount | DECIMAL(20,2) | 元 | 超大单:>= 100 万元或 >= 50 万股 |
| buy_lg_amount | DECIMAL(20,2) | 元 | 大单:20-100 万元或 10-50 万股 |
| buy_md_amount | DECIMAL(20,2) | 元 | 中单:4-20 万 |
| buy_sm_amount | DECIMAL(20,2) | 元 | 小单:< 4 万 |

#### `ods_moneyflow_hsgt`

| 字段 | 单位 | 备注 |
|---|---|---|
| north_money | 元 | 北向 = hgt + sgt |
| south_money | 元 | 南向 = ggt_ss + ggt_sz |

> **2024-08 后口径:** 仅日度总额可用,**个股层级北向数据已废**。`stock_north_funds_daily` 表只有 2024-08 前数据可用。

#### `ods_event_lhb_seat_detail`

| 字段 | 类型 | 口径 |
|---|---|---|
| seat_name | VARCHAR(128) | 营业部全称,需与 `dim_yz_seat.seat_name` 或 `seat_alias` 匹配识别游资 |
| side | ENUM | `buy/sell`,akshare 拆分两个接口需归一化 |
| net_amount | DECIMAL(20,2) | 元,部分席位仅有买/卖单边数据 |

#### `ads_l3_capital_flow` 关键字段

| 字段 | 单位 | 口径 |
|---|---|---|
| mainforce_net_amount | 元 | 全 A 主力净流入合计,**剔除指数 / ETF**(JOIN `vw_security_type` 仅 stock) |
| north_money_5d / 20d | 元 | 滚动 5/20 交易日累计,用 `trade_cal` 取交易日序号 |
| etf_net_inflow_total | 元 | 全部 ETF 当日 share_chg × nav 累加 |
| etf_net_inflow_state | 元 | 仅 `is_state_team=1` 的 ETF |
| if_basis | DECIMAL(16,4) | IF 主力 close - 沪深 300 close,负值贴水 |
| capital_score | 0-100 | 5 项加权,公式见 E2-S2-T8 |

---

### E2-S5 字段映射(数据源 → DB)

#### Tushare `moneyflow` → `ods_moneyflow_stock`

| Tushare 字段 | DB 字段 | 处理 |
|---|---|---|
| `trade_date` | `trade_date` | 直接 |
| `ts_code` | `ts_code` | 直接 |
| `net_mf_amount` | `net_mf_amount` | **×10000 转元**(Tushare 单位万元) |
| `buy_elg_amount` | `buy_elg_amount` | **×10000 转元** |
| `buy_elg_vol` | `buy_elg_vol` | 直接(手数) |

> **强制规则:** 凡 Tushare 标注「万元」字段,入库统一 `×10000` 转元。Antigravity 采集脚本必须在 `pre_load` hook 完成转换。

#### Tushare `moneyflow_hsgt` → `ods_moneyflow_hsgt`

| Tushare | DB | 处理 |
|---|---|---|
| `trade_date` | `trade_date` | 直接 |
| `hgt` | `hgt` | **×100000 转元**(Tushare 单位百万元 = 1e6 元,需确认) |
| `north_money` | `north_money` | 同上 |

> **TBD:** Tushare `moneyflow_hsgt` 单位文档标注百万元,但实测有时返回亿元,Antigravity 需做单位探测脚本。

#### akshare `stock_lhb_detail_em` → `ods_event_lhb_seat_detail`

| akshare 列 | DB 字段 | 处理 |
|---|---|---|
| `代码` | `ts_code` | 拼接交易所后缀(.SH/.SZ/.BJ) |
| `名称` | `stock_name` | 直接 |
| `日期` | `trade_date` | 格式化 |
| `解读` 或 `上榜原因` | `reason` | 直接 |
| `营业部名称` | `seat_name` | 去除前后空格 |
| `买入金额` | `buy_amount` | **× 1 转元**(akshare 默认元) |

#### akshare `fund_etf_fund_info_em` → `ods_etf_share_daily`

| akshare 列 | DB 字段 | 处理 |
|---|---|---|
| `日期` | `trade_date` | - |
| `代码` | `ts_code` | 添加后缀 |
| `份额(亿份)` | `share_total` | 直接 |
| `单位净值` | `nav` | - |
| 派生 | `share_chg` | 当日 - 前一日 |
| 派生 | `net_inflow_est` | `share_chg × nav × 1e8` |

#### Tushare `fut_daily` + `fut_basic` → `ods_fut_daily` / `fut_basic`

| Tushare | DB | 处理 |
|---|---|---|
| 全部字段 | 同名 | `amount × 10000` 转元 |

---

## 技术依赖

| 依赖 | 状态 | 备注 |
|---|---|---|
| 第 1 章 `ods_event_limit_pool` | ✅ 已建 | E1 全部依赖 |
| 第 1 章 `ods_index_daily` | ✅ 已建 | E2-S2-T7 期指基差需要现货 |
| `daily_basic` | ✅ 已存在 | E1 ERP / E2 龙虎榜换手率 |
| `stock_industry_sw` | ✅ 已存在 | E2 龙虎榜行业 enrichment |
| `trade_cal` | ✅ 已存在 | 滚动天数计算必用 |
| Tushare `cn_gov_yield`(或同等接口) | ⚠️ 接口名 TBD | 由 Antigravity 实测确认 |
| Tushare `moneyflow` | ✅ 2000 积分内 | 5400 行/日 |
| Tushare `moneyflow_hsgt` | ✅ 2000 积分内 | 1 行/日 |
| akshare `stock_lhb_detail_em` | ✅ 免费 | 反爬严格,需限速 |
| akshare `fund_etf_fund_info_em` | ✅ 免费 | 1000+ ETF/日 |
| `fut_basic` / `fut_daily` | ✅ 2000 积分内 | 期货 |
| `dim_yz_seat` 数据源 | ⚠️ 手工 | 首批 50-100 席位需手工录入 |

## 风险与避坑

| 风险 | 描述 | 缓解 |
|---|---|---|
| 龙虎榜营业部名称匹配 | 不同源命名差异大,识别游资准确率受影响 | `seat_alias` 别名兜底 + 人工校对前 100 大席位 |
| 北向 2024-08 口径变更 | 个股层数据无法获取 | 前端明确标注口径,只展示总额;个股北向放弃 |
| 涨跌停阈值 9.7% 简化 | 创业板/科创板/北证应分别用 19.7% / 19.7% / 29.7% | 当前简化版会少计部分双创涨停的"连续涨停",**前端必须注明** |
| ETF 单位口径混淆 | akshare 份额单位「亿份」,需 ×1e8 才与净值对齐 | `net_inflow_est` 计算公式锁定为 `share_chg × nav × 1e8` |
| 期指基差仅取主力合约 | 换月期间基差跳变 | 前端展示连续 20 日基差时序图,展示期间换月点 |
| `ads_l4_sentiment.erp_pctile_10y` 冷启动 | 历史 < 10 年时分位失真 | 前端附「样本数」,< 1500 个交易日时降级显示文字「数据不足」 |
| 2024-08 前 `stock_north_funds_daily` 数据 | 仍可用于历史回测,但混用会导致跨期不可比 | 前端时序图仅展示日度总额,不展示个股 |
| MySQL 5.7 变量赋值 ORDER BY 隐性依赖 | 8.0 升级后行为变化 | 实施时改用「按 fut_code 分组取 MAX(vol) 合约 → JOIN」两步法,**避免依赖未文档化行为** |

## 里程碑

| 里程碑 | 内容 | 时点(相对启动 = D0) |
|---|---|---|
| M1 · 表结构落地 | 9 张新表 DDL + dim_yz_seat 首批 50 席位 | D0+1 |
| M2 · ODS 数据回补 | 2024-01 至今 ods_moneyflow_* / lhb / etf / fut | D0+5(由 Antigravity) |
| M3 · L3/L4 计算上线 | 计算 SQL 调度配置,每日 18:00 出数 | D0+7 |
| M4 · 小程序联调 | 接口 + 前端,2 个 tab 上线 | D0+10 |
| M5 · 评分校准 | 1 周观察评分分布,调整归一化分母 | D0+17 |

## 度量指标

| 指标 | 目标 | 监控方式 |
|---|---|---|
| L3/L4 出数延迟 | 盘后 18:30 前 100% | `data_audit_*` 写入时间监控 |
| `ods_moneyflow_stock` 行数偏差 | ±5% vs 前一日 | 行数环比告警 |
| `ods_event_lhb_seat_detail` 缺失 | 当日有龙虎榜则必有数据 | 与 `stock_lhb_daily` 对账 |
| 游资席位识别率 | > 70%(占龙虎榜买卖额) | `lhb_yz_buy / lhb_buy_total` |
| `dim_yz_seat` 别名命中率 | > 90% | 未命中席位 sample 抽查 |
| 计算 SQL 总耗时 | < 30 秒 | 调度框架记录 |

---

## 交付清单确认

| 章 | 建表 SQL | 计算 SQL | 小程序前端 | 数据字典 | 字段映射 |
|---|---|---|---|---|---|
| E1 第 3 章 L4 | ✅ E1-S1 (2 表) | ✅ E1-S2 (T1-T6) | ✅ E1-S3 wxml+wxss+contract | ✅ E1-S4 | ✅ E1-S5 |
| E2 第 4 章 L3 | ✅ E2-S1 (8 表) | ✅ E2-S2 (T1-T8) | ✅ E2-S3 wxml+wxss+contract | ✅ E2-S4 | ✅ E2-S5 |

**下一对话建议:** 第 5 + 6 章(L8 个股异动池 + L6/L9 公告事件与日历)。第 5 章纯计算,无新 ODS,可基于 1-4 章产出快速完成;第 6 章新增 2-3 张事件类 ODS(增减持 / 分红)。两章可并行。