# 第 1 章 · 数据库改造 (E1)

## E1-S1:命名重构

**作为** 数据治理者,**我希望** 将职责模糊的旧表名规范化,**以便** 后续表语义清晰。

#### Task

```sql
-- ============================================
-- E1-S1-T1:旧表重命名
-- ============================================
RENAME TABLE `raw_capital_flow_summary` TO `north_capital_daily`;
RENAME TABLE `raw_sector_daily`         TO `sector_kline_daily`;

-- ============================================
-- E1-S1-T2:为重命名后的表补充注释(可选)
-- ============================================
ALTER TABLE `north_capital_daily`
  COMMENT = 'ODS:北向资金每日净流入(2024-08 后港交所仅披露日终)';

ALTER TABLE `sector_kline_daily`
  COMMENT = 'ODS:行业 / ETF 日线行情';
```

#### AC

- Given 重命名 SQL 执行,When 查询旧表名,Then 报错 `Table doesn't exist`
- Given 业务代码,When 切换到新表名,Then 字段访问无变化(仅表名变更)

---

## E1-S2:新建指数维表

**作为** 盘后系统,**我希望** 有一张权威的指数维表,**以便** 区分核心宽基与一般指数。

#### Task

```sql
-- ============================================
-- E1-S2-T1:指数维表(从 Tushare index_basic 同步)
-- ============================================
CREATE TABLE `index_basic` (
  `ts_code`        VARCHAR(20)   NOT NULL                COMMENT '指数代码,如 000300.SH',
  `name`           VARCHAR(100)                          COMMENT '指数简称,如 沪深300',
  `fullname`       VARCHAR(200)                          COMMENT '指数全称',
  `market`         VARCHAR(20)                           COMMENT '市场,如 SSE/SZSE/CSI/SW',
  `publisher`      VARCHAR(50)                           COMMENT '发布方',
  `index_type`     VARCHAR(50)                           COMMENT '指数风格',
  `category`       VARCHAR(50)                           COMMENT '指数类别(综合/规模/行业/主题/风格/策略/基金/债券)',
  `base_date`      DATE                                  COMMENT '基期',
  `base_point`     DECIMAL(16,4)                         COMMENT '基点',
  `list_date`      DATE                                  COMMENT '发布日期',
  `weight_rule`    VARCHAR(50)                           COMMENT '加权方式',
  `description`    TEXT                                  COMMENT '描述',
  `exp_date`       DATE                                  COMMENT '终止日期(NULL 表示有效)',
  `is_core`        TINYINT(1)    DEFAULT 0               COMMENT '是否核心指数(1=是,0=否),L1 看板只展示核心',
  `display_order`  INT           DEFAULT 999             COMMENT '展示顺序(越小越靠前)',
  `data_source`    VARCHAR(20)   DEFAULT 'tushare'       COMMENT '数据源',
  `created_at`     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`ts_code`),
  KEY `idx_is_core` (`is_core`, `display_order`),
  KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='DIM:指数维表(Tushare index_basic 同步)';

-- ============================================
-- E1-S2-T2:核心指数标记初始化
-- ============================================
-- 注意:以下 INSERT 仅供参考,实际数据由 Antigravity 从 Tushare 拉取后,
--       再执行 UPDATE 设置 is_core 和 display_order
UPDATE `index_basic` SET `is_core` = 1, `display_order` = 1  WHERE `ts_code` = '000001.SH';  -- 上证综指
UPDATE `index_basic` SET `is_core` = 1, `display_order` = 2  WHERE `ts_code` = '399001.SZ';  -- 深证成指
UPDATE `index_basic` SET `is_core` = 1, `display_order` = 3  WHERE `ts_code` = '399006.SZ';  -- 创业板指
UPDATE `index_basic` SET `is_core` = 1, `display_order` = 4  WHERE `ts_code` = '000688.SH';  -- 科创 50
UPDATE `index_basic` SET `is_core` = 1, `display_order` = 5  WHERE `ts_code` = '899050.BJ';  -- 北证 50
UPDATE `index_basic` SET `is_core` = 1, `display_order` = 6  WHERE `ts_code` = '000300.SH';  -- 沪深 300
UPDATE `index_basic` SET `is_core` = 1, `display_order` = 7  WHERE `ts_code` = '000905.SH';  -- 中证 500
UPDATE `index_basic` SET `is_core` = 1, `display_order` = 8  WHERE `ts_code` = '000852.SH';  -- 中证 1000
UPDATE `index_basic` SET `is_core` = 1, `display_order` = 9  WHERE `ts_code` = '932000.CSI'; -- 中证 2000
UPDATE `index_basic` SET `is_core` = 1, `display_order` = 10 WHERE `ts_code` = '8841415.WI'; -- 万得全 A(代码以 Tushare 实际为准,TBD)
```

#### AC

- Given Antigravity 完成首次同步,When 查询 `index_basic`,Then 返回数千条记录
- Given `is_core = 1`,When 查询并按 `display_order` 排序,Then 返回 10 个核心宽基指数

---

## E1-S3:新建指数日线行情表

#### Task

```sql
-- ============================================
-- E1-S3-T1:指数日线 OHLCV
-- ============================================
CREATE TABLE `ods_index_daily` (
  `trade_date`   DATE          NOT NULL                  COMMENT '交易日',
  `ts_code`      VARCHAR(20)   NOT NULL                  COMMENT '指数代码',
  `open`         DECIMAL(16,4)                           COMMENT '开盘点位',
  `high`         DECIMAL(16,4)                           COMMENT '最高点位',
  `low`          DECIMAL(16,4)                           COMMENT '最低点位',
  `close`        DECIMAL(16,4)                           COMMENT '收盘点位',
  `pre_close`    DECIMAL(16,4)                           COMMENT '昨日收盘',
  `change`       DECIMAL(16,4)                           COMMENT '涨跌额',
  `pct_chg`      DECIMAL(10,6)                           COMMENT '涨跌幅(小数,0.0123 = 1.23%)',
  `vol`          DECIMAL(20,2)                           COMMENT '成交量(手,Tushare 原口径)',
  `amount`       DECIMAL(20,2)                           COMMENT '成交额(千元,Tushare 原口径)',
  `data_source`  VARCHAR(20)   DEFAULT 'tushare'         COMMENT '数据源',
  `created_at`   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`trade_date`, `ts_code`),
  KEY `idx_code_date` (`ts_code`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='ODS:指数日线行情(Tushare index_daily 同步)';
```

#### 关键说明

- **`pct_chg` 单位**:Tushare 原口径返回百分比(如 1.23 表示 1.23%),**入库时需 `/ 100` 转换为小数**(0.0123),与全数据库统一口径
- **`amount` 单位**:Tushare 返回千元,本表保持千元口径,展示层换算为亿元
- **不含申万行业指数**:申万指数日线需 5000 积分,本表只承载综合 / 规模 / 主题指数;申万行业指数将在第 2 章用 akshare 单独建表

#### AC

- Given Antigravity 拉取 5 年指数日线,When 查询某核心指数的近 5 年数据,Then 返回 ≈ 1200 行(约 240 交易日 × 5)
- Given `pct_chg`,When 查询任一日,Then 值在 -0.20 ~ 0.20 之间(小数口径)

---

## E1-S4:新建涨跌家数表

#### Task

```sql
-- ============================================
-- E1-S4-T1:全市场涨跌家数(每日一行)
-- 数据源:akshare 自建聚合,从 stock_kline_daily 计算或东财公开接口
-- ============================================
CREATE TABLE `ods_market_breadth_daily` (
  `trade_date`             DATE          NOT NULL          COMMENT '交易日',
  `total_count`            INT                             COMMENT '全 A 总数(剔除 B 股)',
  `up_count`               INT                             COMMENT '上涨家数(pct_chg > 0)',
  `down_count`             INT                             COMMENT '下跌家数(pct_chg < 0)',
  `flat_count`             INT                             COMMENT '平盘家数(pct_chg = 0)',
  `suspended_count`        INT                             COMMENT '停牌家数',
  `up_5pct_count`          INT                             COMMENT '涨幅 ≥ 5% 家数',
  `down_5pct_count`        INT                             COMMENT '跌幅 ≥ 5% 家数',
  `up_9pct_count`          INT                             COMMENT '涨幅 ≥ 9% 家数(接近涨停)',
  `down_9pct_count`        INT                             COMMENT '跌幅 ≥ 9% 家数(接近跌停)',
  `high_60d_count`         INT                             COMMENT '创 60 日新高家数',
  `low_60d_count`          INT                             COMMENT '创 60 日新低家数',
  `high_250d_count`        INT                             COMMENT '创 250 日新高家数(年线新高)',
  `low_250d_count`         INT                             COMMENT '创 250 日新低家数',
  `data_source`            VARCHAR(20)   DEFAULT 'akshare' COMMENT '数据源',
  `created_at`             TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  `updated_at`             TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='ODS:全市场涨跌家数与广度(每日聚合)';
```

#### 关键说明

- **样本范围口径(写死)**:全 A,**剔除 B 股 + 长期停牌(停牌 ≥ 30 日)+ 上市 < 60 日新股**
- **数据获取方式**:Antigravity 实施时,推荐**从 `stock_kline_daily` 自建聚合**(数据可控且可追溯),不依赖外部聚合接口
- **新高新低计算**:基于不复权收盘价 vs 过去 N 日不复权最高 / 最低,口径与展示一致

#### AC

- Given 任一交易日,When 查询,Then `up_count + down_count + flat_count + suspended_count ≈ total_count`(误差 < 1%,允许新股次新股调整)
- Given 牛市行情(指数大涨),When 查询,Then `up_count > down_count` 且 `up_5pct_count > down_5pct_count`

---

## E1-S5:新建涨跌停池表

#### Task

```sql
-- ============================================
-- E1-S5-T1:涨跌停 / 炸板 / 连板池(共表)
-- 数据源:akshare 东财涨跌停池接口(stock_zt_pool_em / stock_dt_pool_em / stock_zt_pool_zbgc_em / stock_zt_pool_previous_em)
-- ============================================
CREATE TABLE `ods_event_limit_pool` (
  `trade_date`        DATE          NOT NULL                COMMENT '交易日',
  `ts_code`           VARCHAR(20)   NOT NULL                COMMENT '股票代码,带后缀如 600519.SH',
  `name`              VARCHAR(50)                           COMMENT '股票名称',
  `pool_type`         VARCHAR(20)   NOT NULL                COMMENT '池类型:zt(涨停)/dt(跌停)/zb(炸板)/lian(连板)',
  `close`             DECIMAL(12,4)                         COMMENT '收盘价',
  `pct_chg`           DECIMAL(10,6)                         COMMENT '涨跌幅(小数)',
  `amount`            DECIMAL(20,2)                         COMMENT '成交额(元)',
  `circ_mv`           DECIMAL(20,2)                         COMMENT '流通市值(元)',
  `turnover_rate`     DECIMAL(10,6)                         COMMENT '换手率(小数)',
  `first_limit_time`  TIME                                  COMMENT '首次封板时间',
  `last_limit_time`   TIME                                  COMMENT '最后封板时间',
  `board_height`      INT           DEFAULT 1               COMMENT '连板高度,首板=1,炸板/跌停为 NULL',
  `seal_money`        DECIMAL(20,2)                         COMMENT '封单金额(元)',
  `seal_count`        INT                                   COMMENT '封板次数(仅涨停池)',
  `open_times`        INT                                   COMMENT '炸板次数(仅炸板池)',
  `industry`          VARCHAR(50)                           COMMENT '所属行业(申万一级,enrichment)',
  `concept_tags`      JSON                                  COMMENT '所属概念列表',
  `data_source`       VARCHAR(20)   DEFAULT 'akshare'       COMMENT '数据源',
  `created_at`        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`trade_date`, `ts_code`, `pool_type`),
  KEY `idx_date_pool` (`trade_date`, `pool_type`),
  KEY `idx_code_date` (`ts_code`, `trade_date`),
  KEY `idx_date_height` (`trade_date`, `board_height`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='ODS:涨跌停 / 炸板 / 连板池(每日多池共表)';
```

#### 关键说明

- **共表设计**:4 种池(`zt` / `dt` / `zb` / `lian`)合并到一张表,通过 `pool_type` 区分,主键 `(trade_date, ts_code, pool_type)` 允许同一只股票同时出现在 `zt` 和 `lian` 池
- **`board_height` 计算**:连板池中,基于昨日 `lian` 池的 `board_height + 1` 递推;首板从 `zt` 池新增
- **涨跌停定义口径(写死)**:
  - 主板 ±10%、创业板 / 科创板 ±20%、北证 ±30%、ST ±5%
  - **以收盘价 = 涨跌停价为准**,不要求当日封板成功
- **pool_type 取值含义**:
  - `zt`:当日涨停股
  - `dt`:当日跌停股
  - `zb`:当日炸板股(曾涨停后打开)
  - `lian`:连板股(连板天数 ≥ 2)

#### AC

- Given 任一交易日,When 查询 `pool_type='zt'`,Then 返回的股票数量 ≈ `ods_market_breadth_daily.up_9pct_count`(允许 ±5 误差)
- Given `pool_type='lian'` 的股票,When 查询其昨日数据,Then 必然存在于昨日 `zt` 或 `lian` 池中
- Given `board_height` 升序,When 查询当日,Then 形成完整的连板梯队(1, 2, 3, ...)

---

## E1-S6:派生指标层 - L1 市场全景

#### Task

```sql
-- ============================================
-- E1-S6-T1:L1 市场全景指标(每日一行)
-- ============================================
CREATE TABLE `ads_l1_market_overview` (
  `trade_date`              DATE          NOT NULL              COMMENT '交易日',

  -- 核心指数收盘(10 个,与 index_basic.is_core=1 对应)
  -- 字段命名规则:idx_<简称>_<指标>
  `idx_sh_close`            DECIMAL(16,4)                       COMMENT '上证综指收盘',
  `idx_sh_pct`              DECIMAL(10,6)                       COMMENT '上证综指涨跌幅(小数)',
  `idx_sz_close`            DECIMAL(16,4)                       COMMENT '深证成指收盘',
  `idx_sz_pct`              DECIMAL(10,6)                       COMMENT '深证成指涨跌幅',
  `idx_cyb_close`           DECIMAL(16,4)                       COMMENT '创业板指收盘',
  `idx_cyb_pct`             DECIMAL(10,6)                       COMMENT '创业板指涨跌幅',
  `idx_kc50_close`          DECIMAL(16,4)                       COMMENT '科创 50 收盘',
  `idx_kc50_pct`            DECIMAL(10,6)                       COMMENT '科创 50 涨跌幅',
  `idx_bz50_close`          DECIMAL(16,4)                       COMMENT '北证 50 收盘',
  `idx_bz50_pct`            DECIMAL(10,6)                       COMMENT '北证 50 涨跌幅',
  `idx_hs300_close`         DECIMAL(16,4)                       COMMENT '沪深 300 收盘',
  `idx_hs300_pct`           DECIMAL(10,6)                       COMMENT '沪深 300 涨跌幅',
  `idx_zz500_close`         DECIMAL(16,4)                       COMMENT '中证 500 收盘',
  `idx_zz500_pct`           DECIMAL(10,6)                       COMMENT '中证 500 涨跌幅',
  `idx_zz1000_close`        DECIMAL(16,4)                       COMMENT '中证 1000 收盘',
  `idx_zz1000_pct`          DECIMAL(10,6)                       COMMENT '中证 1000 涨跌幅',
  `idx_zz2000_close`        DECIMAL(16,4)                       COMMENT '中证 2000 收盘',
  `idx_zz2000_pct`          DECIMAL(10,6)                       COMMENT '中证 2000 涨跌幅',
  `idx_winda_close`         DECIMAL(16,4)                       COMMENT '万得全 A 收盘',
  `idx_winda_pct`           DECIMAL(10,6)                       COMMENT '万得全 A 涨跌幅',

  -- 成交活跃度
  `turnover_total`          DECIMAL(20,2)                       COMMENT '全市场成交额(元)',
  `turnover_ma5`            DECIMAL(20,2)                       COMMENT '成交额 5 日均值(元)',
  `turnover_ma20`           DECIMAL(20,2)                       COMMENT '成交额 20 日均值(元)',
  `turnover_pct_vs_ma20`    DECIMAL(10,6)                       COMMENT '相对 20 日均值倍数 - 1(0.1 = 高出 10%)',
  `turnover_pctile_1y`      DECIMAL(10,6)                       COMMENT '近 1 年(250 交易日)分位数(0-1)',

  -- 涨跌家数
  `up_count`                INT                                 COMMENT '上涨家数',
  `down_count`              INT                                 COMMENT '下跌家数',
  `flat_count`              INT                                 COMMENT '平盘家数',
  `up_down_ratio`           DECIMAL(10,4)                       COMMENT '涨跌比 = up / down',
  `limit_up_count`          INT                                 COMMENT '涨停家数(含一字)',
  `limit_down_count`        INT                                 COMMENT '跌停家数',
  `blast_count`             INT                                 COMMENT '炸板家数',
  `lian_count`              INT                                 COMMENT '连板家数(高度 ≥ 2)',
  `max_board_height`        INT                                 COMMENT '当日最高板高度',
  `high_60d_count`          INT                                 COMMENT '创 60 日新高家数',
  `low_60d_count`           INT                                 COMMENT '创 60 日新低家数',
  `market_breadth`          DECIMAL(10,6)                       COMMENT '市场宽度 = up_count / total_count',

  -- 派生分类
  `market_regime`           VARCHAR(20)                         COMMENT '市场风格:broad_up/broad_down/structural/low_vol',

  -- 审计
  `compute_version`         VARCHAR(20)   DEFAULT 'v1'          COMMENT '计算版本',
  `created_at`              TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  `updated_at`              TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='ADS-L1:市场全景指标(每日一行)';
```

#### AC

- Given 任一交易日,When 查询,Then 仅一行数据
- Given `up_count + down_count + flat_count`,When 计算,Then 大致等于全 A 总数(允许新股 / 停牌偏差)
- Given `market_regime`,When 查询,Then 取值为 4 种之一
