# 第 7 章 · 跨市场 + 估值 + 每日综述 APP

## 背景与目标

**背景**:盘后体系收尾章节,把 L5(估值)、L7(跨市场)、L9(综述与观察清单)三个层级落地。前 6 章的指标在此章被聚合判定,产出"今日复盘"这张前端的主入口。

**目标**:
- 接入海外指数 / 商品 / 汇率 / 利率 4 类外部数据,形成 L7 跨市场视角
- 提供指数与行业的 PE-TTM / PB / 股息率 10 年分位数(L5,周更)
- 输出 `app_daily_brief` 每日综述与 `app_watchlist_next_day` 次日观察清单(L9)
- 微信小程序新增 3 个页面:跨市场、估值分位、每日综述

**范围**:跨市场 ODS 4 张、L5 估值 ADS 2 张、L7 跨市场 ADS 1 张、APP 综述 2 张、小程序 3 个 Tab 页面。

**非目标**:
- 不做 AI 生成自然语言综述(留接口,文本由前端调外部 LLM 生成,本章只产结构化字段)
- 不做衍生品策略层(期权 IV 偏度、隐含波动率曲面等留作后续扩展)
- 商品仅取主力合约连续,不做远期曲线

---

## E1 · 跨市场原始数据层(ODS)

### E1-S1 海外指数日线表

> 作为数据后端,我希望把港股、美股核心指数日线统一存储,以便 L7 综合判定与小程序展示。

#### E1-S1-T1 建表 `ods_index_global_daily`

```sql
-- 海外指数日线(港股 + 美股)
CREATE TABLE IF NOT EXISTS ods_index_global_daily (
    trade_date     DATE          NOT NULL                         COMMENT '交易日(本地)',
    ts_code        VARCHAR(20)   NOT NULL                         COMMENT '指数代码,如 HSI/HSTECH/IXIC/SPX/DJI/VIX',
    market         VARCHAR(8)    NOT NULL                         COMMENT 'HK / US',
    name_cn        VARCHAR(40)   DEFAULT NULL                     COMMENT '中文名',
    open           DECIMAL(16,4) DEFAULT NULL,
    high           DECIMAL(16,4) DEFAULT NULL,
    low            DECIMAL(16,4) DEFAULT NULL,
    close          DECIMAL(16,4) DEFAULT NULL,
    pre_close      DECIMAL(16,4) DEFAULT NULL,
    pct_chg        DECIMAL(10,6) DEFAULT NULL                     COMMENT '小数,0.0123 = 1.23%',
    vol            DECIMAL(20,2) DEFAULT NULL                     COMMENT '成交量(原始单位)',
    amount         DECIMAL(20,2) DEFAULT NULL                     COMMENT '成交额(本币,元)',
    update_time    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code),
    KEY idx_market_date (market, trade_date),
    KEY idx_code_date   (ts_code, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ODS 海外指数日线';

-- 维表:核心海外指数
CREATE TABLE IF NOT EXISTS dim_index_global (
    ts_code     VARCHAR(20)  NOT NULL                 COMMENT '统一代码',
    market      VARCHAR(8)   NOT NULL,
    name_cn     VARCHAR(40)  DEFAULT NULL,
    name_en     VARCHAR(60)  DEFAULT NULL,
    category    VARCHAR(20)  DEFAULT NULL             COMMENT 'broad / tech / risk',
    is_core     TINYINT(1)   DEFAULT 0                COMMENT '1=综述展示',
    sort_order  INT          DEFAULT 999,
    PRIMARY KEY (ts_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='海外指数维表';

-- 初始化
INSERT INTO dim_index_global (ts_code, market, name_cn, name_en, category, is_core, sort_order) VALUES
  ('HSI',    'HK', '恒生指数',     'Hang Seng Index',          'broad', 1, 11),
  ('HSCEI',  'HK', '国企指数',     'HS China Enterprises',     'broad', 1, 12),
  ('HSTECH', 'HK', '恒生科技',     'HS Tech Index',            'tech',  1, 13),
  ('DJI',    'US', '道琼斯',       'Dow Jones Industrial',     'broad', 1, 21),
  ('SPX',    'US', '标普500',      'S&P 500',                  'broad', 1, 22),
  ('IXIC',   'US', '纳斯达克',     'NASDAQ Composite',         'broad', 1, 23),
  ('NDX',    'US', '纳斯达克100',  'NASDAQ 100',               'tech',  0, 24),
  ('VIX',    'US', '恐慌指数',     'CBOE Volatility Index',    'risk',  1, 31)
ON DUPLICATE KEY UPDATE name_cn = VALUES(name_cn);
```

#### E1-S1-T1-AC

- **Given** Antigravity 完成回补,**When** 查询 `HSI` / `SPX` 任意 1 年内交易日,**Then** 返回行数 ≥ 240(剔除两地节假日差异)
- **Given** `pct_chg = -0.0152`,**When** 前端展示,**Then** 渲染为 `-1.52%`
- **Given** 港股交易时间晚于 A 股收盘,**When** 当日 18:00 前查询,**Then** 允许港股缺当日数据但不报错

---

### E1-S2 商品 / 汇率 / 利率日线

> 作为数据后端,我希望把商品、汇率、利率三类时序数据用统一的"主体-数值"结构存储,以便扩展。

#### E1-S2-T1 建表

```sql
-- 商品期货日线(主连)
CREATE TABLE IF NOT EXISTS ods_commodity_daily (
    trade_date    DATE          NOT NULL,
    ts_code       VARCHAR(20)   NOT NULL                          COMMENT '主连代码,如 CL_F/GC_F/AU_S/CU_S/RB_S',
    name_cn       VARCHAR(40)   DEFAULT NULL,
    market        VARCHAR(8)    DEFAULT NULL                      COMMENT 'NYM/CMX/SHF/INE/LME',
    open          DECIMAL(16,4) DEFAULT NULL,
    high          DECIMAL(16,4) DEFAULT NULL,
    low           DECIMAL(16,4) DEFAULT NULL,
    close         DECIMAL(16,4) DEFAULT NULL,
    pre_close     DECIMAL(16,4) DEFAULT NULL,
    pct_chg       DECIMAL(10,6) DEFAULT NULL                      COMMENT '小数',
    settle        DECIMAL(16,4) DEFAULT NULL                      COMMENT '结算价',
    oi            DECIMAL(20,2) DEFAULT NULL                      COMMENT '持仓量',
    vol           DECIMAL(20,2) DEFAULT NULL,
    unit          VARCHAR(20)   DEFAULT NULL                      COMMENT '美元/桶 / 美元/盎司 / 元/吨',
    update_time   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code),
    KEY idx_code_date (ts_code, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ODS 商品主连日线';

-- 汇率日线
CREATE TABLE IF NOT EXISTS ods_fx_daily (
    trade_date    DATE          NOT NULL,
    pair          VARCHAR(12)   NOT NULL                          COMMENT 'USDCNY / USDCNH / EURCNY / JPYCNY / USDJPY',
    name_cn       VARCHAR(40)   DEFAULT NULL,
    open          DECIMAL(12,6) DEFAULT NULL,
    high          DECIMAL(12,6) DEFAULT NULL,
    low           DECIMAL(12,6) DEFAULT NULL,
    close         DECIMAL(12,6) DEFAULT NULL                      COMMENT '收盘价(1 单位前者 = X 后者)',
    pre_close     DECIMAL(12,6) DEFAULT NULL,
    pct_chg       DECIMAL(10,6) DEFAULT NULL,
    update_time   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, pair),
    KEY idx_pair_date (pair, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ODS 汇率日线';

-- 利率日线(短端 + 长端,在岸 + 离岸)
CREATE TABLE IF NOT EXISTS ods_rate_daily (
    trade_date    DATE          NOT NULL,
    rate_code     VARCHAR(20)   NOT NULL                          COMMENT 'shibor_on/1w/1m/3m/1y, cgb_2y/5y/10y, ust_2y/10y, sofr_on',
    name_cn       VARCHAR(40)   DEFAULT NULL,
    rate_value    DECIMAL(10,6) NOT NULL                          COMMENT '年化利率,小数,0.0235 = 2.35%',
    pre_value     DECIMAL(10,6) DEFAULT NULL,
    chg_bp        DECIMAL(10,4) DEFAULT NULL                      COMMENT '环比变动 BP',
    update_time   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, rate_code),
    KEY idx_code_date (rate_code, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ODS 利率日线(在岸+离岸)';
```

#### E1-S2-T1-AC

- **Given** 同一日 `pair=USDCNY` 与 `pair=USDCNH`,**When** 计算价差,**Then** `CNH - CNY` 为离岸偏离,可作为人民币贬值压力信号
- **Given** Shibor 隔夜利率从 1.85% 跳到 2.40%,**When** 入库,**Then** `chg_bp = 55.0000`
- **Given** `rate_value` 全表统一为小数,**When** 跨表汇总,**Then** 不需做单位转换

#### E1-S2-T2 trade-off 说明

| 方案 | 优点 | 缺点 | 选择 |
|---|---|---|---|
| 商品 / 汇率 / 利率合并到一张 `ods_market_cross` | 表少,接入简单 | 字段语义混乱(商品有 OHLC,汇率有 OHLC,利率只有单值),指标维度差异大 | ❌ |
| 按数据形态拆 3 张表 | 字段贴合各自语义,索引高效 | 表多 1 张,采集脚本要改 | ✅ |

---

## E2 · L5 估值层(周更)

### E2-S1 指数估值分位表

> 作为投资者,我希望看到核心宽基指数当前 PE-TTM / PB / 股息率在过去 10 年的分位数,以便判断估值高低。

#### E2-S1-T1 建表 `ads_l5_index_valuation_weekly`

```sql
CREATE TABLE IF NOT EXISTS ads_l5_index_valuation_weekly (
    trade_date         DATE          NOT NULL                    COMMENT '快照日(每周五)',
    ts_code            VARCHAR(20)   NOT NULL                    COMMENT '指数代码',
    name_cn            VARCHAR(40)   DEFAULT NULL,

    -- 当前估值
    pe_ttm             DECIMAL(12,4) DEFAULT NULL                COMMENT 'PE-TTM 中位数加权,剔除负值',
    pb                 DECIMAL(12,4) DEFAULT NULL,
    dv_ratio           DECIMAL(10,6) DEFAULT NULL                COMMENT '股息率(小数)',

    -- 10 年分位(0-1 小数,0.85 = 85% 分位)
    pe_pctile_10y      DECIMAL(10,6) DEFAULT NULL,
    pb_pctile_10y      DECIMAL(10,6) DEFAULT NULL,
    dv_pctile_10y      DECIMAL(10,6) DEFAULT NULL,

    -- 极值参照
    pe_min_10y         DECIMAL(12,4) DEFAULT NULL,
    pe_max_10y         DECIMAL(12,4) DEFAULT NULL,
    pe_median_10y      DECIMAL(12,4) DEFAULT NULL,

    -- 综合标签
    valuation_zone     VARCHAR(16)   DEFAULT NULL                COMMENT 'cheap / fair / rich,基于 pe_pctile_10y',
    sample_days_10y    INT           DEFAULT NULL                COMMENT '样本天数,< 1500 不可信',

    update_time        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code),
    KEY idx_code_date (ts_code, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ADS L5 指数估值周快照';
```

#### E2-S1-T2 计算 SQL(MySQL 5.7 兼容)

> 数据源:Tushare `index_dailybasic`(指数估值),需 Antigravity 接入。**注意 5.7 无窗口函数,分位数用相关子查询。**

```sql
-- ============================================
-- 1. 准备工作:从 ods_index_basic_daily 取 10 年数据
-- ============================================
-- 假设 ods_index_basic_daily 已存在(由 Antigravity 同步 Tushare index_dailybasic)
-- 字段:trade_date, ts_code, total_mv, pe_ttm, pb, dv_ratio
-- 这里 dv_ratio 入库前需 / 100,统一小数口径

-- ============================================
-- 2. 计算当周指数估值分位(10 年回看)
-- ============================================
SET @snap_date := '2026-04-25';   -- 周五
SET @start_date := DATE_SUB(@snap_date, INTERVAL 10 YEAR);

INSERT INTO ads_l5_index_valuation_weekly (
    trade_date, ts_code, name_cn,
    pe_ttm, pb, dv_ratio,
    pe_pctile_10y, pb_pctile_10y, dv_pctile_10y,
    pe_min_10y, pe_max_10y, pe_median_10y,
    valuation_zone, sample_days_10y
)
SELECT
    @snap_date AS trade_date,
    curr.ts_code,
    ib.name AS name_cn,
    curr.pe_ttm,
    curr.pb,
    curr.dv_ratio,

    -- PE 分位:小于等于当前 PE 的样本比例(剔除 PE <= 0)
    (SELECT COUNT(*) FROM ods_index_basic_daily h
     WHERE h.ts_code = curr.ts_code
       AND h.trade_date BETWEEN @start_date AND @snap_date
       AND h.pe_ttm > 0 AND h.pe_ttm <= curr.pe_ttm
    ) / NULLIF((
     SELECT COUNT(*) FROM ods_index_basic_daily h
     WHERE h.ts_code = curr.ts_code
       AND h.trade_date BETWEEN @start_date AND @snap_date
       AND h.pe_ttm > 0
    ), 0) AS pe_pctile_10y,

    -- PB 分位
    (SELECT COUNT(*) FROM ods_index_basic_daily h
     WHERE h.ts_code = curr.ts_code
       AND h.trade_date BETWEEN @start_date AND @snap_date
       AND h.pb > 0 AND h.pb <= curr.pb
    ) / NULLIF((
     SELECT COUNT(*) FROM ods_index_basic_daily h
     WHERE h.ts_code = curr.ts_code
       AND h.trade_date BETWEEN @start_date AND @snap_date
       AND h.pb > 0
    ), 0) AS pb_pctile_10y,

    -- 股息率分位
    (SELECT COUNT(*) FROM ods_index_basic_daily h
     WHERE h.ts_code = curr.ts_code
       AND h.trade_date BETWEEN @start_date AND @snap_date
       AND h.dv_ratio <= curr.dv_ratio
    ) / NULLIF((
     SELECT COUNT(*) FROM ods_index_basic_daily h
     WHERE h.ts_code = curr.ts_code
       AND h.trade_date BETWEEN @start_date AND @snap_date
    ), 0) AS dv_pctile_10y,

    -- 极值
    (SELECT MIN(pe_ttm) FROM ods_index_basic_daily h
     WHERE h.ts_code = curr.ts_code
       AND h.trade_date BETWEEN @start_date AND @snap_date AND h.pe_ttm > 0) AS pe_min_10y,
    (SELECT MAX(pe_ttm) FROM ods_index_basic_daily h
     WHERE h.ts_code = curr.ts_code
       AND h.trade_date BETWEEN @start_date AND @snap_date AND h.pe_ttm > 0) AS pe_max_10y,

    -- 中位数(MySQL 5.7 无 PERCENTILE_CONT,用 GROUP_CONCAT 取中位)
    (SELECT
        SUBSTRING_INDEX(
          SUBSTRING_INDEX(GROUP_CONCAT(pe_ttm ORDER BY pe_ttm), ',', CEIL(COUNT(*)/2)),
          ',', -1) + 0
     FROM ods_index_basic_daily h
     WHERE h.ts_code = curr.ts_code
       AND h.trade_date BETWEEN @start_date AND @snap_date
       AND h.pe_ttm > 0
    ) AS pe_median_10y,

    -- 标签
    CASE
      WHEN curr.pe_ttm IS NULL OR curr.pe_ttm <= 0 THEN 'na'
      WHEN (
        SELECT COUNT(*) FROM ods_index_basic_daily h
        WHERE h.ts_code = curr.ts_code
          AND h.trade_date BETWEEN @start_date AND @snap_date
          AND h.pe_ttm > 0 AND h.pe_ttm <= curr.pe_ttm
      ) / NULLIF((
        SELECT COUNT(*) FROM ods_index_basic_daily h
        WHERE h.ts_code = curr.ts_code
          AND h.trade_date BETWEEN @start_date AND @snap_date
          AND h.pe_ttm > 0
      ), 0) < 0.30 THEN 'cheap'
      WHEN (
        SELECT COUNT(*) FROM ods_index_basic_daily h
        WHERE h.ts_code = curr.ts_code
          AND h.trade_date BETWEEN @start_date AND @snap_date
          AND h.pe_ttm > 0 AND h.pe_ttm <= curr.pe_ttm
      ) / NULLIF((
        SELECT COUNT(*) FROM ods_index_basic_daily h
        WHERE h.ts_code = curr.ts_code
          AND h.trade_date BETWEEN @start_date AND @snap_date
          AND h.pe_ttm > 0
      ), 0) > 0.70 THEN 'rich'
      ELSE 'fair'
    END AS valuation_zone,

    -- 样本天数
    (SELECT COUNT(*) FROM ods_index_basic_daily h
     WHERE h.ts_code = curr.ts_code
       AND h.trade_date BETWEEN @start_date AND @snap_date) AS sample_days_10y

FROM ods_index_basic_daily curr
LEFT JOIN index_basic ib ON curr.ts_code = ib.ts_code
WHERE curr.trade_date = @snap_date
  AND curr.ts_code IN (
    SELECT ts_code FROM index_basic WHERE is_core = 1
  )
ON DUPLICATE KEY UPDATE
    pe_ttm        = VALUES(pe_ttm),
    pb            = VALUES(pb),
    dv_ratio      = VALUES(dv_ratio),
    pe_pctile_10y = VALUES(pe_pctile_10y),
    pb_pctile_10y = VALUES(pb_pctile_10y),
    dv_pctile_10y = VALUES(dv_pctile_10y),
    pe_min_10y    = VALUES(pe_min_10y),
    pe_max_10y    = VALUES(pe_max_10y),
    pe_median_10y = VALUES(pe_median_10y),
    valuation_zone   = VALUES(valuation_zone),
    sample_days_10y  = VALUES(sample_days_10y);
```

#### E2-S1-T2-AC

- **Given** 沪深 300 PE 在 10 年区间为 [9.0, 18.0],当前 PE = 11.5,**When** 跑批,**Then** `pe_pctile_10y` 在 [0.20, 0.40] 区间,`valuation_zone = 'fair'` 或 `'cheap'`
- **Given** 某指数 `sample_days_10y < 1500`,**When** 前端展示,**Then** 标灰 + 提示"样本不足"
- **Given** 同一 `(trade_date, ts_code)` 重复跑批,**When** 第二次执行,**Then** 通过 `ON DUPLICATE KEY UPDATE` 覆盖,不报错

#### E2-S1-T3 trade-off

| 方案 | 优点 | 缺点 | 选择 |
|---|---|---|---|
| 实时算分位(查询时计算) | 数据永远新鲜 | 单次查询 8 个相关子查询,慢 | ❌ |
| 周五跑批落库 + 当日轻量重算 | 性能好,前端快 | 周中数据有延迟 | ✅ |
| 自建定基序列(只存历史 PE 列表) | 中位数 / 分位灵活 | 表膨胀,维护复杂 | 后续考虑 |

---

### E2-S2 行业估值分位表

> 作为投资者,我希望看到申万一级 31 个行业的估值分位,以便横向比较行业冷热。

#### E2-S2-T1 建表 `ads_l5_industry_valuation_weekly`

```sql
CREATE TABLE IF NOT EXISTS ads_l5_industry_valuation_weekly (
    trade_date         DATE          NOT NULL,
    industry_code      VARCHAR(20)   NOT NULL                    COMMENT '申万一级代码',
    industry_name      VARCHAR(40)   DEFAULT NULL,

    -- 加权估值(总市值加权,剔除负 PE 后)
    pe_ttm_wgt         DECIMAL(12,4) DEFAULT NULL,
    pb_wgt             DECIMAL(12,4) DEFAULT NULL,
    dv_ratio_wgt       DECIMAL(10,6) DEFAULT NULL,
    roe_wgt            DECIMAL(10,6) DEFAULT NULL                COMMENT 'ROE 加权(小数)',

    -- 10 年分位(基于行业历史时序)
    pe_pctile_10y      DECIMAL(10,6) DEFAULT NULL,
    pb_pctile_10y      DECIMAL(10,6) DEFAULT NULL,
    dv_pctile_10y      DECIMAL(10,6) DEFAULT NULL,

    -- 综合
    valuation_zone     VARCHAR(16)   DEFAULT NULL,
    constituent_count  INT           DEFAULT NULL                COMMENT '样本股数(剔除 ST 后)',

    update_time        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, industry_code),
    KEY idx_ind_date (industry_code, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ADS L5 行业估值周快照';
```

#### E2-S2-T2 计算 SQL

```sql
-- ============================================
-- 行业估值加权计算
-- 数据源:daily_basic(个股估值) + stock_industry_sw(行业映射)
-- 注意 daily_basic.code 不带后缀,与 stock_industry_sw.code 匹配
-- ============================================

SET @snap_date := '2026-04-25';

-- Step 1: 当周行业加权估值 -> 临时表
DROP TEMPORARY TABLE IF EXISTS tmp_industry_val_curr;
CREATE TEMPORARY TABLE tmp_industry_val_curr AS
SELECT
    sw.industry_code AS industry_code,
    sw.industry_name AS industry_name,

    -- 总市值加权 PE(剔除负 PE 与 ST)
    SUM(CASE WHEN db.pe_ttm > 0 THEN db.pe_ttm * db.total_mv ELSE 0 END)
      / NULLIF(SUM(CASE WHEN db.pe_ttm > 0 THEN db.total_mv ELSE 0 END), 0) AS pe_ttm_wgt,

    SUM(CASE WHEN db.pb > 0 THEN db.pb * db.total_mv ELSE 0 END)
      / NULLIF(SUM(CASE WHEN db.pb > 0 THEN db.total_mv ELSE 0 END), 0) AS pb_wgt,

    -- 股息率加权(/100 转小数)
    SUM(db.dv_ratio / 100 * db.total_mv) / NULLIF(SUM(db.total_mv), 0) AS dv_ratio_wgt,

    COUNT(DISTINCT db.code) AS constituent_count

FROM daily_basic db
INNER JOIN stock_industry_sw sw ON db.code = sw.code
INNER JOIN stock_basic_info  bi ON db.code = bi.code
WHERE db.trade_date = @snap_date
  AND bi.name NOT LIKE '%ST%'           -- 剔除 ST
  AND bi.name NOT LIKE '%退%'           -- 剔除退市
  AND DATEDIFF(@snap_date, bi.list_date) >= 60  -- 上市 ≥ 60 日
  AND sw.industry_code IS NOT NULL
GROUP BY sw.industry_code, sw.industry_name;

-- Step 2: 历史行业加权估值 -> 长表(10 年)
-- 注意:这步开销大,建议 Antigravity 每周五先全量重算入 ods_industry_valuation_history
-- 此处假设该历史快照表已就绪

-- Step 3: 算分位 + 写入目标表
INSERT INTO ads_l5_industry_valuation_weekly (
    trade_date, industry_code, industry_name,
    pe_ttm_wgt, pb_wgt, dv_ratio_wgt,
    pe_pctile_10y, pb_pctile_10y, dv_pctile_10y,
    valuation_zone, constituent_count
)
SELECT
    @snap_date AS trade_date,
    curr.industry_code,
    curr.industry_name,
    curr.pe_ttm_wgt,
    curr.pb_wgt,
    curr.dv_ratio_wgt,

    (SELECT COUNT(*) FROM ods_industry_valuation_history h
     WHERE h.industry_code = curr.industry_code
       AND h.trade_date BETWEEN DATE_SUB(@snap_date, INTERVAL 10 YEAR) AND @snap_date
       AND h.pe_ttm_wgt > 0 AND h.pe_ttm_wgt <= curr.pe_ttm_wgt
    ) / NULLIF((
     SELECT COUNT(*) FROM ods_industry_valuation_history h
     WHERE h.industry_code = curr.industry_code
       AND h.trade_date BETWEEN DATE_SUB(@snap_date, INTERVAL 10 YEAR) AND @snap_date
       AND h.pe_ttm_wgt > 0
    ), 0) AS pe_pctile_10y,

    -- PB / DV 同构,略...
    NULL AS pb_pctile_10y,
    NULL AS dv_pctile_10y,

    CASE
      WHEN curr.pe_ttm_wgt IS NULL THEN 'na'
      -- 简化:实际应用上面计算的 pe_pctile_10y
      ELSE 'fair'
    END AS valuation_zone,

    curr.constituent_count
FROM tmp_industry_val_curr curr
ON DUPLICATE KEY UPDATE
    pe_ttm_wgt        = VALUES(pe_ttm_wgt),
    pb_wgt            = VALUES(pb_wgt),
    dv_ratio_wgt      = VALUES(dv_ratio_wgt),
    pe_pctile_10y     = VALUES(pe_pctile_10y),
    constituent_count = VALUES(constituent_count);
```

#### E2-S2-T2-AC

- **Given** 申万银行行业 31 只成分股都是非 ST,**When** 计算,**Then** `constituent_count >= 30`
- **Given** ROE 入库前未除以 100,**When** 写入,**Then** 在 SELECT 端 `/ 100` 强制转为小数
- **Given** 行业历史快照表 `ods_industry_valuation_history` 缺失,**When** 跑分位计算,**Then** 返回 NULL,不阻塞主流程

---

## E3 · L7 跨市场综合(每日)

### E3-S1 跨市场每日指标表

> 作为决策者,我希望一张表汇总当日海外市场、商品、汇率、利率的关键变化,以便判断对 A 股次日开盘的影响。

#### E3-S1-T1 建表 `ads_l7_cross_market`

```sql
CREATE TABLE IF NOT EXISTS ads_l7_cross_market (
    trade_date              DATE          NOT NULL                COMMENT 'A 股交易日',
    -- 港股(同日)
    hsi_pct_chg             DECIMAL(10,6) DEFAULT NULL,
    hstech_pct_chg          DECIMAL(10,6) DEFAULT NULL,
    hk_southbound_net       DECIMAL(20,2) DEFAULT NULL            COMMENT '南向净买入(元)',

    -- 美股(隔夜,即上一交易日收盘)
    spx_pct_chg             DECIMAL(10,6) DEFAULT NULL,
    nasdaq_pct_chg          DECIMAL(10,6) DEFAULT NULL,
    vix_close               DECIMAL(10,4) DEFAULT NULL,
    vix_chg                 DECIMAL(10,4) DEFAULT NULL,

    -- 商品
    crude_oil_pct           DECIMAL(10,6) DEFAULT NULL            COMMENT 'WTI',
    gold_pct                DECIMAL(10,6) DEFAULT NULL            COMMENT 'COMEX 黄金',
    copper_pct              DECIMAL(10,6) DEFAULT NULL            COMMENT 'LME 铜',
    rebar_pct               DECIMAL(10,6) DEFAULT NULL            COMMENT '螺纹钢主连',

    -- 汇率
    usdcny_close            DECIMAL(12,6) DEFAULT NULL,
    usdcnh_close            DECIMAL(12,6) DEFAULT NULL,
    cnh_minus_cny_bp        DECIMAL(10,4) DEFAULT NULL            COMMENT '离岸-在岸基差(BP),贬值压力指标',
    usdcny_chg_bp           DECIMAL(10,4) DEFAULT NULL,

    -- 利率
    shibor_on               DECIMAL(10,6) DEFAULT NULL,
    shibor_3m               DECIMAL(10,6) DEFAULT NULL,
    cgb_10y                 DECIMAL(10,6) DEFAULT NULL            COMMENT '10 年国债收益率',
    cgb_10y_chg_bp          DECIMAL(10,4) DEFAULT NULL,
    ust_10y                 DECIMAL(10,6) DEFAULT NULL,
    cn_us_10y_spread_bp     DECIMAL(10,4) DEFAULT NULL            COMMENT '中美 10Y 利差(BP)',

    -- 综合判定
    overnight_signal        VARCHAR(16)   DEFAULT NULL            COMMENT 'risk_on / neutral / risk_off',
    overnight_score         DECIMAL(6,2)  DEFAULT NULL            COMMENT '0-100,>60 偏多 <40 偏空',
    overnight_drivers       JSON          DEFAULT NULL            COMMENT '主要驱动因素列表',

    update_time             TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ADS L7 跨市场每日指标';
```

#### E3-S1-T2 计算 SQL

```sql
SET @td := '2026-04-25';
SET @prev_us_td := DATE_SUB(@td, INTERVAL 1 DAY);  -- 美股隔夜口径,实际用 trade_cal 取上一交易日更稳

-- 子查询拼装
INSERT INTO ads_l7_cross_market (
    trade_date,
    hsi_pct_chg, hstech_pct_chg,
    spx_pct_chg, nasdaq_pct_chg, vix_close, vix_chg,
    crude_oil_pct, gold_pct, copper_pct, rebar_pct,
    usdcny_close, usdcnh_close, cnh_minus_cny_bp, usdcny_chg_bp,
    shibor_on, shibor_3m, cgb_10y, cgb_10y_chg_bp, ust_10y, cn_us_10y_spread_bp,
    overnight_signal, overnight_score, overnight_drivers
)
SELECT
    @td,
    -- 港股(同日)
    (SELECT pct_chg FROM ods_index_global_daily WHERE trade_date = @td AND ts_code = 'HSI'),
    (SELECT pct_chg FROM ods_index_global_daily WHERE trade_date = @td AND ts_code = 'HSTECH'),

    -- 美股(取最近一个交易日,用 MAX(trade_date) 兼容假期)
    (SELECT pct_chg FROM ods_index_global_daily
       WHERE ts_code = 'SPX' AND trade_date < @td
       ORDER BY trade_date DESC LIMIT 1),
    (SELECT pct_chg FROM ods_index_global_daily
       WHERE ts_code = 'IXIC' AND trade_date < @td
       ORDER BY trade_date DESC LIMIT 1),
    (SELECT close   FROM ods_index_global_daily
       WHERE ts_code = 'VIX' AND trade_date < @td
       ORDER BY trade_date DESC LIMIT 1),
    (SELECT close - pre_close FROM ods_index_global_daily
       WHERE ts_code = 'VIX' AND trade_date < @td
       ORDER BY trade_date DESC LIMIT 1),

    -- 商品
    (SELECT pct_chg FROM ods_commodity_daily WHERE trade_date = @td AND ts_code = 'CL_F'),
    (SELECT pct_chg FROM ods_commodity_daily WHERE trade_date = @td AND ts_code = 'GC_F'),
    (SELECT pct_chg FROM ods_commodity_daily WHERE trade_date = @td AND ts_code = 'CU_LME'),
    (SELECT pct_chg FROM ods_commodity_daily WHERE trade_date = @td AND ts_code = 'RB_S'),

    -- 汇率
    (SELECT close FROM ods_fx_daily WHERE trade_date = @td AND pair = 'USDCNY'),
    (SELECT close FROM ods_fx_daily WHERE trade_date = @td AND pair = 'USDCNH'),
    -- 离岸-在岸基差,人民币贬值压力指标
    (
      (SELECT close FROM ods_fx_daily WHERE trade_date = @td AND pair = 'USDCNH') -
      (SELECT close FROM ods_fx_daily WHERE trade_date = @td AND pair = 'USDCNY')
    ) * 10000 AS cnh_minus_cny_bp,
    (
      (SELECT close - pre_close FROM ods_fx_daily WHERE trade_date = @td AND pair = 'USDCNY')
    ) * 10000 AS usdcny_chg_bp,

    -- 利率
    (SELECT rate_value FROM ods_rate_daily WHERE trade_date = @td AND rate_code = 'shibor_on'),
    (SELECT rate_value FROM ods_rate_daily WHERE trade_date = @td AND rate_code = 'shibor_3m'),
    (SELECT rate_value FROM ods_rate_daily WHERE trade_date = @td AND rate_code = 'cgb_10y'),
    (SELECT chg_bp     FROM ods_rate_daily WHERE trade_date = @td AND rate_code = 'cgb_10y'),
    (SELECT rate_value FROM ods_rate_daily WHERE trade_date = @td AND rate_code = 'ust_10y'),
    (
      (SELECT rate_value FROM ods_rate_daily WHERE trade_date = @td AND rate_code = 'cgb_10y') -
      (SELECT rate_value FROM ods_rate_daily WHERE trade_date = @td AND rate_code = 'ust_10y')
    ) * 10000 AS cn_us_10y_spread_bp,

    -- 综合信号(简化版规则,后续可调权)
    NULL AS overnight_signal,
    NULL AS overnight_score,
    NULL AS overnight_drivers

ON DUPLICATE KEY UPDATE
    hsi_pct_chg     = VALUES(hsi_pct_chg),
    spx_pct_chg     = VALUES(spx_pct_chg),
    vix_close       = VALUES(vix_close),
    crude_oil_pct   = VALUES(crude_oil_pct),
    usdcnh_close    = VALUES(usdcnh_close),
    cgb_10y         = VALUES(cgb_10y);

-- ============================================
-- 二次更新:综合信号打分
-- ============================================
UPDATE ads_l7_cross_market
SET
    overnight_score =
        50  -- 基线
        + (COALESCE(spx_pct_chg, 0) * 100 * 5)         -- 标普 +1% 加 5 分
        + (COALESCE(nasdaq_pct_chg, 0) * 100 * 3)      -- 纳指 +1% 加 3 分
        + (COALESCE(hsi_pct_chg, 0) * 100 * 4)         -- 恒指 +1% 加 4 分
        - (COALESCE(vix_chg, 0) * 2)                   -- VIX +1 减 2 分
        - (CASE WHEN cnh_minus_cny_bp > 100 THEN 5 ELSE 0 END)  -- 离岸贬值压力 -5
        + (CASE WHEN cgb_10y_chg_bp < -3 THEN 3 ELSE 0 END)     -- 国债下行,流动性宽松 +3
    ,
    overnight_signal = CASE
        WHEN overnight_score >= 60 THEN 'risk_on'
        WHEN overnight_score <= 40 THEN 'risk_off'
        ELSE 'neutral'
    END
WHERE trade_date = @td;
```

#### E3-S1-T2-AC

- **Given** 美股周末休市,**When** 周一 A 股开盘前查询,**Then** `spx_pct_chg` 取上周五数值,不为 NULL
- **Given** `cnh_minus_cny_bp = 250`,**When** 综合打分,**Then** `overnight_score` 至少减 5
- **Given** VIX 单日跳升 5 点,**When** 计算,**Then** `vix_chg = 5.0` 且 `overnight_score` 减 10

---

## E4 · L9 决策综述与观察清单(APP 层)

### E4-S1 每日综述总表

> 作为用户,我希望小程序首页能看到一张今日复盘卡片,包含市场判定、主线、风险、明日要点,以便 5 分钟把握全局。

#### E4-S1-T1 建表 `app_daily_brief`

```sql
CREATE TABLE IF NOT EXISTS app_daily_brief (
    trade_date              DATE          NOT NULL,

    -- 总判定(综合 L1-L8 加权)
    market_judgement        VARCHAR(16)   DEFAULT NULL            COMMENT 'strong_bull/bull/neutral/bear/strong_bear',
    judgement_score         DECIMAL(6,2)  DEFAULT NULL            COMMENT '0-100',

    -- 一句话标题(供前端 H1 展示)
    headline                VARCHAR(120)  DEFAULT NULL            COMMENT '如:沪指放量收阳,半导体接力上攻',

    -- 6 维分项分数
    breadth_score           DECIMAL(6,2)  DEFAULT NULL            COMMENT 'L1 涨跌家数比 → 分',
    sentiment_score         DECIMAL(6,2)  DEFAULT NULL            COMMENT 'L4 连板 + 赚钱效应',
    capital_score           DECIMAL(6,2)  DEFAULT NULL            COMMENT 'L3 主力 + 北向 + 两融',
    valuation_score         DECIMAL(6,2)  DEFAULT NULL            COMMENT 'L5 估值分位反转',
    cross_market_score      DECIMAL(6,2)  DEFAULT NULL            COMMENT 'L7 隔夜信号',
    event_score             DECIMAL(6,2)  DEFAULT NULL            COMMENT 'L6 事件驱动',

    -- 主线(JSON 数组)
    main_themes             JSON          DEFAULT NULL            COMMENT '[{theme,leaders[],strength,持续性}]',

    -- 异象 / 风险
    risk_warnings           JSON          DEFAULT NULL            COMMENT '[{type,desc,severity}]',

    -- 次日要点
    next_day_focus          JSON          DEFAULT NULL            COMMENT '{events[],sectors[],levels{sh,sz}}',

    -- 综述长文(可选,供 LLM 生成接入)
    summary_text            TEXT          DEFAULT NULL,
    summary_generated_at    DATETIME      DEFAULT NULL,

    update_time             TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='APP 每日综述';
```

#### E4-S1-T2 计算 SQL(综合打分)

```sql
SET @td := '2026-04-25';

-- ============================================
-- 6 维分项 → 综合打分
-- ============================================
INSERT INTO app_daily_brief (
    trade_date,
    breadth_score, sentiment_score, capital_score,
    valuation_score, cross_market_score, event_score,
    judgement_score, market_judgement, headline,
    main_themes, risk_warnings, next_day_focus
)
SELECT
    @td,

    -- 1) 涨跌家数维度(L1)
    -- 涨跌比 1:1 = 50 分,2:1 = 70 分,1:2 = 30 分
    LEAST(100, GREATEST(0,
        50 + (l1.up_count - l1.down_count) / NULLIF(l1.up_count + l1.down_count, 0) * 50
    )) AS breadth_score,

    -- 2) 情绪维度(L4)
    -- 涨停 ≥ 跌停 ×3 + 高度 ≥ 5 = 偏强
    LEAST(100, GREATEST(0,
        50
        + LEAST(30, (l4.limit_up_count - l4.limit_down_count) * 0.5)
        + LEAST(20, COALESCE(l4.max_board_height, 0) * 3)
    )) AS sentiment_score,

    -- 3) 资金维度(L3)
    -- 北向净买入 + 主力净流入
    LEAST(100, GREATEST(0,
        50
        + LEAST(25, COALESCE(l3.northbound_net_amt, 0) / 1e9 * 5)   -- 每 10 亿 +5
        + LEAST(25, COALESCE(l3.main_net_amt_total, 0) / 1e10 * 5)  -- 每 100 亿 +5
    )) AS capital_score,

    -- 4) 估值维度(L5,反转分:分位低则分高)
    LEAST(100, GREATEST(0,
        100 - COALESCE(l5.pe_pctile_10y, 0.5) * 100
    )) AS valuation_score,

    -- 5) 跨市场维度(L7)
    COALESCE(l7.overnight_score, 50) AS cross_market_score,

    -- 6) 事件维度(L6)
    -- 业绩超预期 + 回购增持为正,减持 + 解禁为负
    LEAST(100, GREATEST(0, 50 + COALESCE(l6.event_net_score, 0))) AS event_score,

    -- ===== 综合分(加权) =====
    -- breadth 20 / sentiment 25 / capital 25 / valuation 10 / cross 10 / event 10
    LEAST(100, GREATEST(0,
        LEAST(100, GREATEST(0,
            50 + (l1.up_count - l1.down_count) / NULLIF(l1.up_count + l1.down_count, 0) * 50
        )) * 0.20
        + LEAST(100, GREATEST(0,
            50 + LEAST(30, (l4.limit_up_count - l4.limit_down_count) * 0.5)
               + LEAST(20, COALESCE(l4.max_board_height, 0) * 3)
        )) * 0.25
        + LEAST(100, GREATEST(0,
            50 + LEAST(25, COALESCE(l3.northbound_net_amt, 0) / 1e9 * 5)
               + LEAST(25, COALESCE(l3.main_net_amt_total, 0) / 1e10 * 5)
        )) * 0.25
        + LEAST(100, GREATEST(0,
            100 - COALESCE(l5.pe_pctile_10y, 0.5) * 100
        )) * 0.10
        + COALESCE(l7.overnight_score, 50) * 0.10
        + LEAST(100, GREATEST(0, 50 + COALESCE(l6.event_net_score, 0))) * 0.10
    )) AS judgement_score,

    -- 综合判定(基于 judgement_score)
    CASE
        WHEN (
            -- 重新算一遍 judgement_score(MySQL 5.7 不能引用 SELECT 别名)
            ... -- 实操中拆为两步:第一步 INSERT,第二步 UPDATE 写 judgement
            1
        ) > 0 THEN 'neutral'
        ELSE 'neutral'
    END AS market_judgement,

    -- headline / themes / risk / next_day_focus 留空,由后续 UPDATE 步骤填入
    NULL AS headline,
    NULL AS main_themes,
    NULL AS risk_warnings,
    NULL AS next_day_focus

FROM (SELECT @td AS dt) d
LEFT JOIN ads_l1_market_overview     l1 ON l1.trade_date = @td
LEFT JOIN ads_l4_sentiment           l4 ON l4.trade_date = @td
LEFT JOIN ads_l3_capital_flow        l3 ON l3.trade_date = @td
LEFT JOIN ads_l7_cross_market        l7 ON l7.trade_date = @td
LEFT JOIN (
    -- L5 取沪深 300 分位作为代表
    SELECT trade_date, pe_pctile_10y
    FROM ads_l5_index_valuation_weekly
    WHERE ts_code = '000300.SH'
      AND trade_date <= @td
    ORDER BY trade_date DESC LIMIT 1
) l5 ON 1=1
LEFT JOIN (
    -- L6 简化:净事件分 = 业绩预喜数 - 业绩预亏数 + 回购数 - 减持数
    SELECT @td AS trade_date,
           (perf_increase_count - perf_decrease_count
            + buyback_count
            - holder_decrease_count) * 0.5 AS event_net_score
    FROM ads_l6_event_daily
    WHERE trade_date = @td
) l6 ON 1=1
ON DUPLICATE KEY UPDATE
    breadth_score      = VALUES(breadth_score),
    sentiment_score    = VALUES(sentiment_score),
    capital_score      = VALUES(capital_score),
    valuation_score    = VALUES(valuation_score),
    cross_market_score = VALUES(cross_market_score),
    event_score        = VALUES(event_score),
    judgement_score    = VALUES(judgement_score);

-- ============================================
-- 第二步:基于 judgement_score 写 market_judgement
-- ============================================
UPDATE app_daily_brief
SET market_judgement = CASE
    WHEN judgement_score >= 75 THEN 'strong_bull'
    WHEN judgement_score >= 60 THEN 'bull'
    WHEN judgement_score >= 40 THEN 'neutral'
    WHEN judgement_score >= 25 THEN 'bear'
    ELSE 'strong_bear'
END
WHERE trade_date = @td;

-- ============================================
-- 第三步:写主线 themes(JSON,从 L2 取 main_theme)
-- ============================================
UPDATE app_daily_brief b
INNER JOIN (
    SELECT
        trade_date,
        JSON_ARRAYAGG(JSON_OBJECT(
            'theme',       industry_name,
            'pct_chg',     pct_chg,
            'main_force',  main_net_amt,
            'leaders',     leader_stocks,
            'sustain_days', sustain_days
        )) AS themes_json
    FROM ads_l2_industry_daily
    WHERE trade_date = @td
      AND theme_label = 'main_theme'
    GROUP BY trade_date
) t ON b.trade_date = t.trade_date
SET b.main_themes = t.themes_json
WHERE b.trade_date = @td;

-- ============================================
-- 第四步:写 headline(规则模板)
-- ============================================
UPDATE app_daily_brief b
INNER JOIN ads_l1_market_overview l1 ON b.trade_date = l1.trade_date
SET b.headline = CONCAT(
    CASE
      WHEN l1.sh_pct_chg > 0.01 THEN '沪指放量收阳'
      WHEN l1.sh_pct_chg > 0    THEN '沪指小幅红盘'
      WHEN l1.sh_pct_chg > -0.01 THEN '沪指小幅回调'
      ELSE '沪指放量回调'
    END,
    ',',
    CASE b.market_judgement
      WHEN 'strong_bull' THEN '情绪显著回暖'
      WHEN 'bull'        THEN '情绪偏强'
      WHEN 'neutral'     THEN '结构性分化'
      WHEN 'bear'        THEN '情绪偏弱'
      ELSE '风险偏好回落'
    END
)
WHERE b.trade_date = @td;

-- ============================================
-- 第五步:风险警示(JSON,基于规则)
-- ============================================
UPDATE app_daily_brief b
INNER JOIN ads_l4_sentiment      s ON b.trade_date = s.trade_date
INNER JOIN ads_l7_cross_market   c ON b.trade_date = c.trade_date
SET b.risk_warnings = JSON_ARRAY(
    CASE WHEN s.blast_rate > 0.40
         THEN JSON_OBJECT('type','炸板高发','severity','high','desc',CONCAT('炸板率',ROUND(s.blast_rate*100,1),'%'))
         ELSE NULL END,
    CASE WHEN c.cnh_minus_cny_bp > 200
         THEN JSON_OBJECT('type','汇率贬压','severity','medium','desc',CONCAT('CNH-CNY ',ROUND(c.cnh_minus_cny_bp,0),' BP'))
         ELSE NULL END,
    CASE WHEN c.vix_chg > 3
         THEN JSON_OBJECT('type','海外避险','severity','medium','desc',CONCAT('VIX 跳升 ',ROUND(c.vix_chg,1)))
         ELSE NULL END
)
WHERE b.trade_date = @td;

-- 注:JSON_ARRAY 包含 NULL 时建议在前端过滤,或改用 JSON_ARRAYAGG + WHERE 条件构造
```

#### E4-S1-T2-AC

- **Given** L1 涨家 4500 跌家 800,北向净流入 80 亿,涨停 80 跌停 5,**When** 跑批,**Then** `judgement_score >= 70`,`market_judgement = 'bull'` 或 `'strong_bull'`
- **Given** 任一上游 ADS 表缺数,**When** 跑批,**Then** 对应分项 `COALESCE` 兜底为 50,主流程不中断
- **Given** 同日重跑,**When** 第二次执行,**Then** 通过 `ON DUPLICATE KEY UPDATE` 覆盖最新结果

#### E4-S1-T3 trade-off

| 方案 | 优点 | 缺点 | 选择 |
|---|---|---|---|
| 综述文本由 SQL 模板拼接 | 完全可控,无外部依赖 | 表达僵硬,套话多 | 部分(headline) |
| 综述文本由 LLM 生成 | 流畅自然,有判断 | 成本 + 时延 + 偶发幻觉 | 留接口,前端调用 |
| 6 维分项 + 总分 | 量化可追溯,各维独立可调 | 权重需要校准 | ✅ |

---

### E4-S2 次日观察清单

> 作为用户,我希望小程序展示明日重点关注的个股池,带分类标签与关注理由。

#### E4-S2-T1 建表 `app_watchlist_next_day`

```sql
CREATE TABLE IF NOT EXISTS app_watchlist_next_day (
    trade_date          DATE          NOT NULL                COMMENT '生成日(下一交易日为观察日)',
    next_trade_date     DATE          NOT NULL                COMMENT '观察日',
    ts_code             VARCHAR(12)   NOT NULL,
    name                VARCHAR(40)   DEFAULT NULL,
    industry            VARCHAR(40)   DEFAULT NULL,

    watch_type          VARCHAR(24)   NOT NULL                COMMENT 'limit_up_continue/breakout/event_driven/theme_leader/lhb_focus/capital_in/anomaly_followup',
    watch_reason        VARCHAR(200)  DEFAULT NULL            COMMENT '一句话理由',
    priority            TINYINT       DEFAULT 5               COMMENT '1-10,10 最高',

    -- 关键参考价位
    close_price         DECIMAL(16,4) DEFAULT NULL,
    suggest_buy_zone    VARCHAR(40)   DEFAULT NULL            COMMENT '建议关注区间,如 12.50-13.20',
    stop_loss           DECIMAL(16,4) DEFAULT NULL,

    -- 关键指标快照
    snapshot            JSON          DEFAULT NULL            COMMENT '{board_height,seal_money,main_net,industry_rank,...}',

    -- 关联事件
    related_event       VARCHAR(200)  DEFAULT NULL            COMMENT '如:Q1 业绩预增 200%',

    update_time         TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code, watch_type),
    KEY idx_priority (trade_date, priority DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='APP 次日观察清单';
```

#### E4-S2-T2 计算 SQL

```sql
SET @td := '2026-04-25';
SET @next_td := (SELECT MIN(cal_date) FROM trade_cal
                 WHERE cal_date > @td AND is_open = 1);

-- ============================================
-- 类型 1:连板续涨候选(高度 ≥ 2 且封单强)
-- ============================================
INSERT INTO app_watchlist_next_day (
    trade_date, next_trade_date, ts_code, name, industry,
    watch_type, watch_reason, priority,
    close_price, snapshot
)
SELECT
    @td, @next_td,
    p.ts_code,
    bi.name,
    sw.industry_name,
    'limit_up_continue',
    CONCAT(p.board_height, '板,封单 ', ROUND(p.seal_money/1e8, 1), ' 亿'),
    LEAST(10, 5 + p.board_height),
    k.close,
    JSON_OBJECT(
        'board_height', p.board_height,
        'seal_money',   p.seal_money,
        'open_times',   p.open_times,
        'industry',     sw.industry_name
    )
FROM ods_event_limit_pool p
INNER JOIN stock_basic_info bi ON p.ts_code = bi.code   -- 假设 ts_code 已转 code 或用映射
INNER JOIN stock_industry_sw sw ON sw.code = bi.code
LEFT JOIN stock_kline_daily k ON k.code = bi.code AND k.trade_date = @td
WHERE p.trade_date = @td
  AND p.pool_type = 'zt'
  AND p.board_height >= 2
  AND p.seal_money >= 5e7   -- 封单 ≥ 5000 万
  AND p.open_times <= 2     -- 炸板 ≤ 2 次
ON DUPLICATE KEY UPDATE
    watch_reason = VALUES(watch_reason),
    priority     = VALUES(priority);

-- ============================================
-- 类型 2:主线龙头(L2 main_theme + 行业前 3)
-- ============================================
INSERT INTO app_watchlist_next_day (
    trade_date, next_trade_date, ts_code, name, industry,
    watch_type, watch_reason, priority, snapshot
)
SELECT
    @td, @next_td,
    leader_code AS ts_code,
    leader_name AS name,
    industry_name,
    'theme_leader',
    CONCAT('主线 ', industry_name, ' 龙头(行业排名第 1)'),
    8,
    JSON_OBJECT(
        'theme',          industry_name,
        'industry_pct',   pct_chg,
        'sustain_days',   sustain_days,
        'main_net_amt',   main_net_amt
    )
FROM (
    -- 假设 L2 表里有 leader_stocks JSON,提取 [0] 作为龙头
    SELECT
        industry_code,
        industry_name,
        pct_chg,
        sustain_days,
        main_net_amt,
        JSON_UNQUOTE(JSON_EXTRACT(leader_stocks, '$[0].code')) AS leader_code,
        JSON_UNQUOTE(JSON_EXTRACT(leader_stocks, '$[0].name')) AS leader_name
    FROM ads_l2_industry_daily
    WHERE trade_date = @td
      AND theme_label = 'main_theme'
) x
WHERE leader_code IS NOT NULL
ON DUPLICATE KEY UPDATE priority = VALUES(priority);

-- ============================================
-- 类型 3:事件驱动(明天有业绩预告 / 解禁 / 增持)
-- 此处仅示意,具体字段以第 6 章为准
-- ============================================
INSERT INTO app_watchlist_next_day (
    trade_date, next_trade_date, ts_code, name, industry,
    watch_type, watch_reason, priority, related_event
)
SELECT
    @td, @next_td,
    e.ts_code, bi.name, sw.industry_name,
    'event_driven',
    CONCAT(e.event_type, ': ', e.event_desc),
    7,
    e.event_desc
FROM ads_l9_calendar_upcoming e
LEFT JOIN stock_basic_info  bi ON e.ts_code = bi.code
LEFT JOIN stock_industry_sw sw ON sw.code  = bi.code
WHERE e.event_date = @next_td
  AND e.event_type IN ('业绩预告','解禁','回购实施','增持完成')
ON DUPLICATE KEY UPDATE related_event = VALUES(related_event);

-- ============================================
-- 类型 4:龙虎榜知名游资 / 机构净买入(L3)
-- ============================================
INSERT INTO app_watchlist_next_day (
    trade_date, next_trade_date, ts_code, name, industry,
    watch_type, watch_reason, priority, snapshot
)
SELECT
    @td, @next_td,
    l.ts_code, l.name, l.industry,
    'lhb_focus',
    CONCAT('龙虎榜 ', l.top_seat_name, ' 净买 ', ROUND(l.top_seat_net/1e7,1), ' 千万'),
    6,
    JSON_OBJECT(
        'top_seat',     l.top_seat_name,
        'seat_net',     l.top_seat_net,
        'inst_net',     l.inst_net_amt
    )
FROM ads_l3_lhb_focus l                 -- 假设第 4 章有此 view 或表
WHERE l.trade_date = @td
  AND l.top_seat_yz_flag = 1            -- 知名游资席位
ON DUPLICATE KEY UPDATE watch_reason = VALUES(watch_reason);
```

#### E4-S2-T2-AC

- **Given** 同一只股票同时满足"连板续涨"与"主线龙头",**When** 写入,**Then** 产生 2 条记录(主键含 `watch_type`),前端按 priority 去重
- **Given** `next_trade_date` 是节后第一个交易日,**When** `trade_cal` 被正确使用,**Then** 不会出现自然日 +1 误差
- **Given** 知名游资席位库 `dim_yz_seat` 缺失,**When** 类型 4 跑批,**Then** 该类型为空,其他类型不受影响

---

## E5 · 微信小程序前端(3 个页面)

### E5-S1 每日综述页(首页 / 主入口)

> 作为用户,我希望打开 APP 5 秒内看清今日市场判定与最关键 3 件事。

#### E5-S1-T1 wxml `pages/brief/index.wxml`

```xml
<scroll-view class="page-scroll" scroll-y enable-back-to-top>
  <view class="page-wrap">

    <!-- ===== 综述卡片(主) ===== -->
    <view class="card brief-card">
      <view class="card-side-bar"></view>

      <view class="brief-header">
        <view class="brief-date mono">{{brief.tradeDateLabel}}</view>
        <view class="brief-judgement judge-{{brief.market_judgement}}">
          <text class="j-label">{{brief.judgementCn}}</text>
          <text class="j-score mono">{{brief.judgement_score}}</text>
        </view>
      </view>

      <view class="brief-headline">{{brief.headline}}</view>

      <!-- 6 维雷达指标 -->
      <view class="six-dim">
        <view class="dim-item" wx:for="{{brief.dims}}" wx:key="key">
          <view class="dim-label">{{item.label}}</view>
          <view class="dim-bar">
            <view class="dim-bar-fill" style="width: {{item.score}}%; background: {{item.color}}"></view>
          </view>
          <view class="dim-score mono">{{item.score}}</view>
        </view>
      </view>
    </view>

    <!-- ===== 主线题材 ===== -->
    <view class="card">
      <view class="card-side-bar"></view>
      <view class="card-header">
        <view class="card-title-cn">主线题材</view>
        <view class="card-title-en">MAIN THEMES</view>
      </view>
      <view class="theme-list">
        <view class="theme-row" wx:for="{{brief.main_themes}}" wx:key="theme">
          <view class="theme-rank mono">{{index + 1}}</view>
          <view class="theme-body">
            <view class="theme-name-row">
              <text class="theme-name">{{item.theme}}</text>
              <text class="theme-pct mono {{item.pct_chg >= 0 ? 'up' : 'down'}}">
                {{item.pct_chg >= 0 ? '+' : ''}}{{item.pct_chg_pct}}%
              </text>
            </view>
            <view class="theme-leaders mono">{{item.leaders_text}}</view>
            <view class="theme-meta">
              <text class="meta-tag">持续 {{item.sustain_days}}日</text>
              <text class="meta-tag">主力 {{item.main_force_yi}}亿</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- ===== 风险警示 ===== -->
    <view class="card" wx:if="{{brief.risk_warnings.length}}">
      <view class="card-side-bar bar-alert"></view>
      <view class="card-header">
        <view class="card-title-cn">风险警示</view>
        <view class="card-title-en">RISK ALERTS</view>
      </view>
      <view class="risk-list">
        <view class="risk-item" wx:for="{{brief.risk_warnings}}" wx:key="type">
          <view class="risk-dot dot-{{item.severity}}"></view>
          <view class="risk-body">
            <text class="risk-type">{{item.type}}</text>
            <text class="risk-desc">{{item.desc}}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- ===== 次日观察 ===== -->
    <view class="card">
      <view class="card-side-bar"></view>
      <view class="card-header">
        <view class="card-title-cn">次日观察</view>
        <view class="card-title-en">NEXT DAY</view>
      </view>
      <view class="watch-tabs">
        <view class="watch-tab {{watchTab === item.key ? 'active' : ''}}"
              wx:for="{{watchTabs}}" wx:key="key"
              bindtap="switchWatchTab" data-key="{{item.key}}">
          {{item.label}} <text class="watch-count mono">{{item.count}}</text>
        </view>
      </view>
      <view class="watch-list">
        <view class="watch-row" wx:for="{{currentWatchList}}" wx:key="ts_code">
          <view class="watch-rank mono">{{index + 1}}</view>
          <view class="watch-main">
            <view class="watch-line1">
              <text class="watch-name">{{item.name}}</text>
              <text class="watch-code mono">{{item.ts_code}}</text>
            </view>
            <view class="watch-reason">{{item.watch_reason}}</view>
          </view>
          <view class="watch-priority">
            <view class="prio-bar">
              <view class="prio-fill" style="width: {{item.priority * 10}}%"></view>
            </view>
          </view>
        </view>
      </view>
    </view>

  </view>
</scroll-view>
```

#### E5-S1-T2 wxss `pages/brief/index.wxss`

```css
@import '/styles/tokens.wxss';

.page-wrap { padding: 16rpx; }

/* ===== 综述卡片 ===== */
.brief-card {
  padding: 32rpx 32rpx 32rpx 40rpx;
  background: linear-gradient(180deg, var(--bg-elev) 0%, var(--bg-card) 60%);
}

.brief-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20rpx;
}
.brief-date {
  font-size: 24rpx;
  color: var(--ink-mute);
  letter-spacing: 4rpx;
}

.brief-judgement {
  display: flex; align-items: baseline; gap: 12rpx;
  padding: 4rpx 16rpx;
  border: 1rpx solid var(--hair);
}
.j-label { font-size: 24rpx; letter-spacing: 2rpx; }
.j-score { font-size: 28rpx; font-weight: 600; }

.judge-strong_bull { color: var(--up); border-color: var(--up); }
.judge-bull        { color: var(--up); }
.judge-neutral     { color: var(--ink-dim); }
.judge-bear        { color: var(--down); }
.judge-strong_bear { color: var(--down); border-color: var(--down); }

.brief-headline {
  font-size: 36rpx;
  line-height: 1.5;
  color: var(--ink);
  font-weight: 600;
  margin: 24rpx 0 32rpx;
  letter-spacing: 1rpx;
}

/* 6 维分项 */
.six-dim {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16rpx 32rpx;
  padding-top: 16rpx; border-top: 1rpx solid var(--hair);
}
.dim-item {
  display: grid;
  grid-template-columns: 110rpx 1fr 60rpx;
  align-items: center;
  gap: 12rpx;
}
.dim-label { font-size: 24rpx; color: var(--ink-dim); }
.dim-bar {
  height: 6rpx; background: var(--hair); border-radius: 3rpx; overflow: hidden;
}
.dim-bar-fill { height: 100%; transition: width .3s; }
.dim-score { font-size: 24rpx; color: var(--ink); text-align: right; }

/* ===== 主线题材 ===== */
.theme-list { display: flex; flex-direction: column; }
.theme-row {
  display: grid;
  grid-template-columns: 50rpx 1fr;
  gap: 20rpx;
  padding: 24rpx 0;
  border-bottom: 1rpx solid var(--hair);
}
.theme-row:last-child { border-bottom: none; }
.theme-rank {
  font-size: 36rpx; color: var(--amber); font-weight: 300;
  text-align: center; line-height: 1;
}
.theme-name-row {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 8rpx;
}
.theme-name { font-size: 30rpx; font-weight: 600; color: var(--ink); }
.theme-pct  { font-size: 28rpx; }

.theme-leaders {
  font-size: 24rpx; color: var(--ink-dim);
  margin-bottom: 8rpx;
}

.theme-meta { display: flex; gap: 16rpx; }
.meta-tag {
  font-size: 22rpx; color: var(--ink-mute);
  padding: 2rpx 8rpx;
  border: 1rpx solid var(--hair);
}

/* ===== 风险警示 ===== */
.bar-alert { background: var(--alert) !important; }
.risk-list { display: flex; flex-direction: column; gap: 16rpx; }
.risk-item {
  display: grid; grid-template-columns: 16rpx 1fr; gap: 16rpx; align-items: start;
}
.risk-dot {
  width: 12rpx; height: 12rpx; border-radius: 50%;
  margin-top: 12rpx;
}
.dot-high   { background: var(--weak); box-shadow: 0 0 8rpx var(--weak); }
.dot-medium { background: var(--alert); box-shadow: 0 0 6rpx var(--alert); }
.dot-low    { background: var(--neutral); }
.risk-type {
  font-size: 26rpx; font-weight: 600; color: var(--ink);
  margin-right: 12rpx;
}
.risk-desc { font-size: 24rpx; color: var(--ink-dim); }

/* ===== 次日观察 ===== */
.watch-tabs {
  display: flex; gap: 32rpx;
  border-bottom: 1rpx solid var(--hair);
  margin-bottom: 16rpx;
}
.watch-tab {
  font-size: 26rpx; color: var(--ink-dim);
  padding: 16rpx 0;
  position: relative;
}
.watch-tab.active {
  color: var(--amber);
}
.watch-tab.active::after {
  content: ''; position: absolute; bottom: -1rpx; left: 0; right: 0;
  height: 2rpx; background: var(--amber);
}
.watch-count {
  font-size: 22rpx; color: var(--ink-mute); margin-left: 4rpx;
}

.watch-row {
  display: grid;
  grid-template-columns: 50rpx 1fr 80rpx;
  gap: 16rpx; align-items: center;
  padding: 20rpx 0;
  border-bottom: 1rpx solid var(--hair);
}
.watch-row:last-child { border-bottom: none; }
.watch-rank { color: var(--amber); font-size: 28rpx; text-align: center; }
.watch-line1 { display: flex; align-items: baseline; gap: 12rpx; margin-bottom: 4rpx; }
.watch-name { font-size: 28rpx; font-weight: 600; color: var(--ink); }
.watch-code { font-size: 22rpx; color: var(--ink-mute); }
.watch-reason { font-size: 24rpx; color: var(--ink-dim); }

.prio-bar {
  width: 60rpx; height: 4rpx; background: var(--hair);
  margin-left: auto;
}
.prio-fill { height: 100%; background: var(--amber); }
```

---

### E5-S2 跨市场页

> 作为用户,我希望一屏看清港美股、商品、汇率、利率四类隔夜变化。

#### E5-S2-T1 wxml(片段)

```xml
<scroll-view class="page-scroll" scroll-y>
  <view class="page-wrap">

    <!-- 隔夜信号横条 -->
    <view class="overnight-banner banner-{{cross.overnight_signal}}">
      <text class="banner-label">隔夜信号</text>
      <text class="banner-value">{{cross.overnightSignalCn}}</text>
      <text class="banner-score mono">{{cross.overnight_score}}</text>
    </view>

    <!-- 港美股 -->
    <view class="card">
      <view class="card-side-bar"></view>
      <view class="card-header">
        <view class="card-title-cn">港美股市</view>
        <view class="card-title-en">HK / US</view>
      </view>
      <view class="idx-grid">
        <view class="idx-cell" wx:for="{{cross.indices}}" wx:key="ts_code">
          <view class="idx-name">{{item.name_cn}}</view>
          <view class="idx-close mono">{{item.closeFmt}}</view>
          <view class="idx-pct mono {{item.pct_chg >= 0 ? 'up' : 'down'}}">
            {{item.pct_chg >= 0 ? '+' : ''}}{{item.pct_chg_pct}}%
          </view>
        </view>
      </view>
    </view>

    <!-- 商品 -->
    <view class="card">
      <view class="card-side-bar"></view>
      <view class="card-header">
        <view class="card-title-cn">大宗商品</view>
        <view class="card-title-en">COMMODITIES</view>
      </view>
      <view class="cmd-list">
        <view class="cmd-row" wx:for="{{cross.commodities}}" wx:key="ts_code">
          <text class="cmd-name">{{item.name_cn}}</text>
          <text class="cmd-close mono">{{item.closeFmt}} {{item.unit}}</text>
          <text class="cmd-pct mono {{item.pct_chg >= 0 ? 'up' : 'down'}}">
            {{item.pct_chg >= 0 ? '+' : ''}}{{item.pct_chg_pct}}%
          </text>
        </view>
      </view>
    </view>

    <!-- 汇率 + 利率 双栏 -->
    <view class="dual-cards">
      <view class="card half-card">
        <view class="card-side-bar"></view>
        <view class="card-header">
          <view class="card-title-cn">汇率</view>
          <view class="card-title-en">FX</view>
        </view>
        <view class="kv-row" wx:for="{{cross.fx}}" wx:key="pair">
          <text class="kv-label">{{item.name_cn}}</text>
          <text class="kv-value mono">{{item.closeFmt}}</text>
          <text class="kv-chg mono {{item.up ? 'up' : 'down'}}">{{item.chgBpFmt}} BP</text>
        </view>
        <view class="cnh-spread">
          <text class="spread-label">CNH-CNY 基差</text>
          <text class="spread-value mono {{cross.cnh_basis_alert ? 'alert' : ''}}">
            {{cross.cnh_minus_cny_bp}} BP
          </text>
        </view>
      </view>

      <view class="card half-card">
        <view class="card-side-bar"></view>
        <view class="card-header">
          <view class="card-title-cn">利率</view>
          <view class="card-title-en">RATES</view>
        </view>
        <view class="kv-row" wx:for="{{cross.rates}}" wx:key="rate_code">
          <text class="kv-label">{{item.name_cn}}</text>
          <text class="kv-value mono">{{item.valueFmt}}%</text>
          <text class="kv-chg mono {{item.chg_bp >= 0 ? 'up' : 'down'}}">
            {{item.chg_bp >= 0 ? '+' : ''}}{{item.chg_bp}} BP
          </text>
        </view>
        <view class="spread-row">
          <text class="spread-label">中美 10Y 利差</text>
          <text class="spread-value mono">{{cross.cn_us_spread}} BP</text>
        </view>
      </view>
    </view>

  </view>
</scroll-view>
```

#### E5-S2-T2 关键 wxss

```css
.overnight-banner {
  display: flex; align-items: center; gap: 16rpx;
  padding: 20rpx 32rpx;
  margin-bottom: 16rpx;
  background: var(--bg-card);
  border-left: 4rpx solid var(--amber);
}
.banner-{risk_on}    { border-left-color: var(--up); }
.banner-{neutral}    { border-left-color: var(--amber); }
.banner-{risk_off}   { border-left-color: var(--down); }
.banner-label { font-size: 24rpx; color: var(--ink-mute); letter-spacing: 2rpx; }
.banner-value { font-size: 28rpx; color: var(--ink); margin-left: auto; }
.banner-score { font-size: 32rpx; color: var(--amber); font-weight: 600; }

.idx-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 1rpx;
  background: var(--hair);
}
.idx-cell {
  background: var(--bg-card);
  padding: 20rpx 24rpx;
  display: flex; flex-direction: column; gap: 6rpx;
}
.idx-name  { font-size: 26rpx; color: var(--ink-dim); }
.idx-close { font-size: 32rpx; color: var(--ink); font-weight: 600; }
.idx-pct   { font-size: 24rpx; }

.cmd-row {
  display: grid; grid-template-columns: 1fr auto auto;
  gap: 16rpx; padding: 16rpx 0;
  border-bottom: 1rpx solid var(--hair);
}
.cmd-row:last-child { border-bottom: none; }
.cmd-name  { font-size: 26rpx; color: var(--ink-dim); }
.cmd-close { font-size: 24rpx; color: var(--ink); }
.cmd-pct   { font-size: 24rpx; min-width: 100rpx; text-align: right; }

.dual-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 16rpx; }
.half-card { padding: 20rpx 16rpx 20rpx 24rpx; }

.kv-row {
  display: grid; grid-template-columns: 80rpx 1fr auto;
  gap: 8rpx; padding: 12rpx 0;
  border-bottom: 1rpx solid var(--hair);
}
.kv-row:last-child { border-bottom: none; }
.kv-label { font-size: 22rpx; color: var(--ink-mute); }
.kv-value { font-size: 24rpx; color: var(--ink); }
.kv-chg   { font-size: 20rpx; text-align: right; }

.cnh-spread, .spread-row {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-top: 16rpx; padding-top: 16rpx;
  border-top: 1rpx solid var(--hair);
}
.spread-label { font-size: 22rpx; color: var(--ink-mute); }
.spread-value { font-size: 26rpx; color: var(--ink); font-weight: 600; }
.spread-value.alert { color: var(--alert); }
```

---

### E5-S3 估值分位页

> 作为投资者,我希望一屏看清核心宽基与申万行业的估值分位,直观判断高低。

#### E5-S3-T1 wxml(片段)

```xml
<view class="page-wrap">

  <!-- Tab 切换:指数 / 行业 -->
  <view class="seg-tabs">
    <view class="seg-tab {{tab === 'index' ? 'active' : ''}}" bindtap="switchTab" data-tab="index">
      宽基指数
    </view>
    <view class="seg-tab {{tab === 'industry' ? 'active' : ''}}" bindtap="switchTab" data-tab="industry">
      申万一级
    </view>
  </view>

  <!-- 估值列表 -->
  <view class="card">
    <view class="card-side-bar"></view>
    <view class="card-header">
      <view class="card-title-cn">{{tab === 'index' ? '指数估值分位' : '行业估值分位'}}</view>
      <view class="card-title-en">VALUATION · 10Y</view>
    </view>

    <view class="val-list">
      <view class="val-row" wx:for="{{currentList}}" wx:key="ts_code">
        <view class="val-name-col">
          <view class="val-name">{{item.name_cn}}</view>
          <view class="val-pe mono">PE {{item.pe_ttm_fmt}}</view>
        </view>

        <!-- 分位条 -->
        <view class="val-bar-col">
          <view class="val-bar-track">
            <view class="val-bar-zone zone-cheap"></view>
            <view class="val-bar-zone zone-fair"></view>
            <view class="val-bar-zone zone-rich"></view>
            <view class="val-bar-marker"
                  style="left: {{item.pe_pctile_pct}}%"></view>
          </view>
          <view class="val-bar-meta">
            <text class="meta-min mono">{{item.pe_min_10y_fmt}}</text>
            <text class="meta-zone zone-{{item.valuation_zone}}">{{item.zoneCn}}</text>
            <text class="meta-max mono">{{item.pe_max_10y_fmt}}</text>
          </view>
        </view>

        <view class="val-pct-col mono">{{item.pe_pctile_pct}}%</view>
      </view>
    </view>
  </view>

</view>
```

#### E5-S3-T2 关键 wxss

```css
.seg-tabs {
  display: flex; margin-bottom: 16rpx;
  border: 1rpx solid var(--hair);
}
.seg-tab {
  flex: 1; text-align: center;
  padding: 20rpx 0; font-size: 26rpx;
  color: var(--ink-dim);
  border-right: 1rpx solid var(--hair);
}
.seg-tab:last-child { border-right: none; }
.seg-tab.active {
  background: var(--bg-elev);
  color: var(--amber);
}

.val-row {
  display: grid;
  grid-template-columns: 160rpx 1fr 80rpx;
  gap: 16rpx; align-items: center;
  padding: 24rpx 0;
  border-bottom: 1rpx solid var(--hair);
}
.val-row:last-child { border-bottom: none; }

.val-name { font-size: 28rpx; color: var(--ink); font-weight: 600; }
.val-pe { font-size: 22rpx; color: var(--ink-mute); margin-top: 4rpx; }

.val-bar-track {
  position: relative;
  height: 16rpx;
  display: flex;
  border: 1rpx solid var(--hair);
}
.val-bar-zone { height: 100%; }
.zone-cheap { width: 30%; background: rgba(138,181,115,0.30); }
.zone-fair  { width: 40%; background: rgba(212,162,62,0.20); }
.zone-rich  { width: 30%; background: rgba(229,100,79,0.30); }

.val-bar-marker {
  position: absolute; top: -4rpx; bottom: -4rpx;
  width: 4rpx;
  background: var(--amber-bright);
  box-shadow: 0 0 8rpx var(--amber-bright);
}

.val-bar-meta {
  display: flex; justify-content: space-between;
  margin-top: 8rpx;
  font-size: 20rpx;
}
.meta-min, .meta-max { color: var(--ink-mute); }
.meta-zone { font-size: 22rpx; font-weight: 600; }
.zone-cheap { color: var(--strong); background: transparent; }
.zone-fair  { color: var(--neutral); background: transparent; }
.zone-rich  { color: var(--weak); background: transparent; }

.val-pct-col {
  font-size: 32rpx; color: var(--ink); font-weight: 600;
  text-align: right;
}
```

#### E5-S3-T3 数据接口契约(后端要返的 JSON)

```json
{
  "trade_date": "2026-04-25",
  "index_list": [
    {
      "ts_code": "000300.SH",
      "name_cn": "沪深300",
      "pe_ttm": 12.45,
      "pe_pctile_10y": 0.32,
      "valuation_zone": "fair",
      "pe_min_10y": 8.50,
      "pe_max_10y": 18.20,
      "pe_median_10y": 12.80,
      "sample_days_10y": 2435
    }
  ],
  "industry_list": [
    {
      "industry_code": "801080.SI",
      "industry_name": "电子",
      "pe_ttm_wgt": 38.5,
      "pe_pctile_10y": 0.62,
      "valuation_zone": "fair",
      "constituent_count": 320
    }
  ]
}
```

---

## E6 · 数据字典(第 7 章新增/变更)

### E6-S1 表清单

| 表名 | 层 | 频次 | 主键 | 行数估算 | 用途 |
|---|---|---|---|---|---|
| `dim_index_global` | DIM | 静态 | `ts_code` | ~10 | 港美股核心指数维表 |
| `ods_index_global_daily` | ODS | 日 | `(trade_date, ts_code)` | ~80/日 | 港美股指数日线 |
| `ods_index_basic_daily` | ODS | 日 | `(trade_date, ts_code)` | ~30/日 | 指数估值原始(Tushare) |
| `ods_industry_valuation_history` | ODS | 周 | `(trade_date, industry_code)` | ~31/周 | 行业估值历史(回算) |
| `ods_commodity_daily` | ODS | 日 | `(trade_date, ts_code)` | ~10/日 | 商品主连日线 |
| `ods_fx_daily` | ODS | 日 | `(trade_date, pair)` | ~5/日 | 汇率日线 |
| `ods_rate_daily` | ODS | 日 | `(trade_date, rate_code)` | ~12/日 | 在岸+离岸利率 |
| `ads_l5_index_valuation_weekly` | ADS | 周 | `(trade_date, ts_code)` | ~10/周 | 指数估值分位 |
| `ads_l5_industry_valuation_weekly` | ADS | 周 | `(trade_date, industry_code)` | ~31/周 | 行业估值分位 |
| `ads_l7_cross_market` | ADS | 日 | `trade_date` | 1/日 | 跨市场综合 |
| `app_daily_brief` | APP | 日 | `trade_date` | 1/日 | 每日综述 |
| `app_watchlist_next_day` | APP | 日 | `(trade_date, ts_code, watch_type)` | ~30/日 | 次日观察清单 |

### E6-S2 关键字段口径

| 字段 | 类型 | 单位 | 口径说明 |
|---|---|---|---|
| `pct_chg`(全表) | DECIMAL(10,6) | 小数 | `0.0125 = +1.25%`,与全库统一 |
| `rate_value` | DECIMAL(10,6) | 小数 | `0.0235 = 2.35%`,年化 |
| `chg_bp` | DECIMAL(10,4) | BP | `1 BP = 0.0001`,即 `(rate - pre) * 10000` |
| `pe_pctile_10y` | DECIMAL(10,6) | 0-1 | 当前 PE 在过去 10 年(剔除负值)的分位 |
| `valuation_zone` | ENUM | - | `cheap` (<0.30) / `fair` (0.30-0.70) / `rich` (>0.70) / `na` |
| `judgement_score` | DECIMAL(6,2) | 0-100 | 综合 6 维加权,见 E4-S1-T2 |
| `market_judgement` | ENUM | - | `strong_bull` ≥75 / `bull` ≥60 / `neutral` ≥40 / `bear` ≥25 / `strong_bear` <25 |
| `cnh_minus_cny_bp` | DECIMAL(10,4) | BP | 离岸-在岸 USDCNY 基差,>200 BP 视为贬压信号 |
| `cn_us_10y_spread_bp` | DECIMAL(10,4) | BP | 中国 10Y - 美国 10Y |
| `vix_close` | DECIMAL(10,4) | 点 | 不做小数化,VIX 是水平值 |
| `priority`(观察清单) | TINYINT | 1-10 | 10 最优先,前端按 DESC 排 |

### E6-S3 watch_type 枚举

| 枚举值 | 含义 | 优先级基准 |
|---|---|---|
| `limit_up_continue` | 连板续涨候选 | 5+板高 |
| `breakout` | 突破长期均线 / 平台 | 6 |
| `event_driven` | 业绩 / 公告驱动 | 7 |
| `theme_leader` | 主线龙头 | 8 |
| `lhb_focus` | 龙虎榜知名席位 | 6 |
| `capital_in` | 主力大单流入 | 5 |
| `anomaly_followup` | 异动复跟踪(L8) | 5 |

### E6-S4 valuation_zone 阈值

```
分位 < 0.30  → cheap   (绿,可关注)
分位 0.30-0.70 → fair   (黄,中性)
分位 > 0.70  → rich    (红,谨慎)
样本不足 1500 日 → na    (灰,不可信)
```

---

## E7 · 字段映射(数据源 → DB,供 Antigravity)

### E7-S1 海外指数

| Tushare 接口 | akshare 接口 | DB 表 | 字段映射 |
|---|---|---|---|
| `hk_index_daily(ts_code='HSI')` | `index_hk_hist`<br>(symbol='HSI') | `ods_index_global_daily` | trade_date, ts_code, open, high, low, close, pre_close, **`pct_chg / 100`**, vol, amount |
| `index_global(ts_code='SPX')` | `index_us_stock_sina`<br>(symbol='.INX') | `ods_index_global_daily` | 同上 |
| - | `index_us_stock_sina`<br>(symbol='VIX') | `ods_index_global_daily` | 同上,`vol`/`amount` 可为 NULL |

**注意:**
- Tushare 港股需 5000 积分,2000 积分用户用 akshare 兜底
- akshare 美股代号写法:`.INX`(标普)、`.IXIC`(纳指)、`.DJI`(道指)、`VIX`
- `pct_chg` 各源单位不一,**Antigravity 入库前必须统一除以 100**

### E7-S2 商品

| 数据源 | 标的 | DB 字段 ts_code |
|---|---|---|
| Tushare `fut_daily` | 螺纹钢主连 | `RB_S` |
| akshare `futures_main_sina` | 沪铜主连 | `CU_S` |
| akshare `futures_foreign_commodity_subscribe`(WTI 主连) | NYMEX 原油 | `CL_F` |
| akshare `futures_foreign_commodity_subscribe`(COMEX 黄金) | COMEX 黄金 | `GC_F` |
| akshare `futures_zh_realtime` 或 LME 数据 | LME 铜 | `CU_LME` |

`unit` 字段由 Antigravity 写死(`美元/桶`、`美元/盎司`、`元/吨`、`美元/磅`)。

### E7-S3 汇率

| 数据源 | pair |
|---|---|
| akshare `currency_boc_sina`(中行牌价) | USDCNY、EURCNY、JPYCNY |
| akshare `currency_hist_fx_spot`(银联) | USDCNH(离岸) |
| Tushare `fx_daily` | USDJPY、EURUSD |

**注意:** USDCNY 取**中间价**(每日 9:15 公布),USDCNH 取**收盘价**(24h 行情)。

### E7-S4 利率

| 数据源 | rate_code |
|---|---|
| Tushare `shibor` | `shibor_on`、`shibor_1w`、`shibor_1m`、`shibor_3m`、`shibor_1y` |
| Tushare `cn_gdp_yearly` 不适用 — 用 `bond_yield_10y`(自建) | `cgb_2y`、`cgb_5y`、`cgb_10y` |
| akshare `bond_zh_us_rate` | `cgb_10y`、`ust_10y` |
| akshare `rate_interbank` | `sofr_on`、`ust_2y` |

**Tushare Shibor 接口字段:** `on`、`1w`、`1m`、`3m`、`1y`,**入库前要 `/100`** 转小数。

### E7-S5 指数估值原始

| 数据源 | 接口 | 入库表 |
|---|---|---|
| Tushare | `index_dailybasic(ts_code, trade_date, ...)` | `ods_index_basic_daily` |
| 字段: | `total_mv`(亿元)→ `* 1e8` 转元 / `pe_ttm` / `pb` / `dv_ratio`(%)→ `/100` 转小数 | |

### E7-S6 采集脚本配置(YAML 示例,供 Antigravity)

```yaml
# 第 7 章数据采集配置
# 文件位置:antigravity/configs/chapter_07.yml

ods_index_global_daily:
  source: akshare
  function: index_hk_hist | index_us_stock_sina
  schedule: "30 9 * * 1-5"   # 港股 09:30 后(实际 16:30 收盘后,但日内更新)
  schedule_us: "00 5 * * 1-5"  # 美股次日 05:00 北京时间
  history_years: 10
  unit_transform:
    pct_chg: "value / 100"
  primary_key: [trade_date, ts_code]

ods_commodity_daily:
  source: tushare + akshare
  schedule: "30 9 * * 1-5"
  symbols:
    - {ts_code: CL_F,  source: akshare, name_cn: WTI原油, unit: 美元/桶}
    - {ts_code: GC_F,  source: akshare, name_cn: COMEX黄金, unit: 美元/盎司}
    - {ts_code: CU_LME,source: akshare, name_cn: LME铜,  unit: 美元/吨}
    - {ts_code: RB_S,  source: tushare, name_cn: 螺纹钢主连, unit: 元/吨, fut_code: RB.SHF}
  history_years: 5

ods_fx_daily:
  source: akshare
  schedule: "20 9 * * 1-5"
  pairs:
    - {pair: USDCNY,  type: middle_rate}    # 中间价
    - {pair: USDCNH,  type: close}          # 离岸收盘
    - {pair: EURCNY,  type: middle_rate}
    - {pair: JPYCNY,  type: middle_rate}
  history_years: 10

ods_rate_daily:
  source: tushare + akshare
  schedule: "30 11 * * 1-5"   # Shibor 上午 11:00 公布
  rates:
    - {rate_code: shibor_on, source: tushare, fn: shibor, field: "on"}
    - {rate_code: shibor_3m, source: tushare, fn: shibor, field: "3m"}
    - {rate_code: cgb_10y,   source: akshare, fn: bond_zh_us_rate}
    - {rate_code: ust_10y,   source: akshare, fn: bond_zh_us_rate}
  unit_transform:
    rate_value: "value / 100"
  history_years: 10

ods_index_basic_daily:
  source: tushare
  function: index_dailybasic
  schedule: "00 17 * * 1-5"
  index_codes:
    - 000001.SH
    - 000300.SH
    - 000905.SH
    - 000852.SH
    - 932000.CSI
    - 000985.SH
    - 399006.SZ
    - 000688.SH
  unit_transform:
    total_mv: "value * 1e8"
    dv_ratio: "value / 100"
  history_years: 10
```

---

## 技术依赖

- **第 1 章**:`ads_l1_market_overview` / `ods_event_limit_pool` / `index_basic`(综述打分依赖)
- **第 2 章**:`ads_l2_industry_daily.theme_label = 'main_theme'`(主线题材)
- **第 3 章**:`ads_l4_sentiment`(情绪分维度)
- **第 4 章**:`ads_l3_capital_flow`(资金分维度)
- **第 6 章**:`ads_l6_event_daily` / `ads_l9_calendar_upcoming`(事件分 + 次日事件)
- **数据源**:Tushare 2000 积分(指数基本面、Shibor)+ akshare(港美股、商品、汇率)
- **MySQL 5.7** 兼容:全程相关子查询替代窗口函数,中位数用 `GROUP_CONCAT` + `SUBSTRING_INDEX` 套路

---

## 风险与避坑

1. **Tushare 港股权限**:`hk_index_daily` 可能需 5000 积分,**2000 积分必须用 akshare 兜底**,Antigravity 实施前先验证
2. **VIX 没有 `pct_chg` 概念**:VIX 是水平值,前端展示用绝对变动(`vix_chg`),不要除 100
3. **美股交易日与 A 股错位**:周一查美股要回看上周五,代码里用 `ORDER BY trade_date DESC LIMIT 1` 而非 `DATE_SUB(@td, 1 DAY)`
4. **Shibor 公布时间在 11:00**:综述打分跑批要排在 11:30 之后,否则当日 Shibor 缺失
5. **PE 中位数 SQL 性能**:`GROUP_CONCAT` 在 10 年 2500 行数据上没问题,但若回看 20 年要调 `group_concat_max_len`,默认 1024 会截断
6. **CNH-CNY 基差精度**:DECIMAL(12,6) 算到小数点后 6 位,*10000 后 BP 单位足够
7. **行业估值历史快照**:`ods_industry_valuation_history` 实施时建议 Antigravity 每周末**全量回算最近 10 年**,而非增量,避免成分股变化导致的口径漂移
8. **JSON_ARRAYAGG 行为**:MySQL 5.7.22 之前不支持 `JSON_ARRAYAGG`,**实施前确认 MySQL 小版本** ≥ 5.7.22,否则降级用 `GROUP_CONCAT` + 应用层拼装
9. **综述打分权重需校准**:首版权重(20/25/25/10/10/10)是先验值,运行 1 个月后用历史数据回测调整 — TBD
10. **`headline` 模板僵硬**:规则模板生成的标题会重复,生产建议接 LLM(成本约 ¥0.01/天,可控)— TBD

---

## 里程碑

| 节点 | 交付 |
|---|---|
| D+1 | DDL 全部建表 + dim 数据初始化 |
| D+3 | Antigravity 完成 ODS 4 张表的实时 + 历史回补(10 年) |
| D+5 | 计算 SQL 跑通,L5 / L7 / APP 三层落库 |
| D+7 | 小程序 3 个页面接入数据,首屏可用 |
| D+10 | 综述打分权重校准(基于 1 周历史回测) |
| D+14 | LLM 综述文本接入(可选) |

---

## 度量指标

- **数据完整性**:`ads_l7_cross_market.trade_date = 当日` 且无 NULL 字段(允许 VIX 周一缺失)
- **综述打分稳定性**:7 日内 `judgement_score` 标准差 < 30(过大则权重不合理)
- **观察清单命中率**:`watchlist` 次日实际涨幅前 50 中占比(目标 ≥ 30%)
- **首页加载性能**:`app_daily_brief` 单行查询 < 50ms(主键查询应该 < 5ms)
- **采集稳定性**:Antigravity 4 张 ODS 表每日 17:30 前可用率 ≥ 95%

---

## 全体系收尾说明

第 7 章交付后,7 章全部闭环:

```
L1 市场全景    ✅ 第 1 章
L2 结构分化    ✅ 第 2 章
L3 资金层      ✅ 第 4 章
L4 情绪层      ✅ 第 3 章
L5 估值层      ✅ 第 7 章(本章)
L6 事件层      ✅ 第 6 章
L7 跨市场      ✅ 第 7 章(本章)
L8 异动层      ✅ 第 5 章
L9 决策准备    ✅ 第 6 章 + 第 7 章(本章)

APP 综述       ✅ 第 7 章(本章)
```

小程序最终 5 个 Tab 建议:
1. **复盘**(第 7 章 brief 页,**首页**)
2. **市场**(第 1 章 全景 + 第 2 章 行业)
3. **资金**(第 4 章)
4. **机会**(第 3 章 情绪 + 第 5 章 异动 + 第 7 章 观察清单)
5. **日历**(第 6 章 事件 + 第 7 章 跨市场)

至此盘后体系前后端 + 数据全部交付完毕。