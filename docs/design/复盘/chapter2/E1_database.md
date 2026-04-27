# 第 2 章 · 数据库改造 (E1)

## E1-S1: 维表整合与复用 (DIM)

**作为** 数据架构师, **我希望** 充分利用 MySQL 中已有的行业与板块维表, **以便** 保持数据口径一致并减少冗余。

#### 关键说明

- **申万行业**: 直接复用已有表 `stock_industry_sw`。该表已包含 `l1/l2/l3` 三级映射，本章 L2 层级主要使用其 `l1_code` (一级行业) 进行聚合。
- **概念板块**: 直接复用已有表 `stock_sector_ths` (字典) 与 `stock_sector_cons_ths` (成分映射)。
- **风格因子**: 新建 `dim_style_factor` 表，用于定义“大盘 vs 小盘”等强弱对比组合。

#### Task: 新建风格因子定义表

```sql
-- ============================================
-- E1-S1-T1: 风格因子定义维表
-- ============================================
CREATE TABLE IF NOT EXISTS `dim_style_factor` (
  `factor_code`     VARCHAR(30)   NOT NULL                COMMENT '因子代码, 如 large_vs_small',
  `factor_name`     VARCHAR(50)                           COMMENT '因子中文名, 如 大小盘强弱',
  `long_index`      VARCHAR(20)                           COMMENT '多头指数代码 (对应 index_basic)',
  `long_name`       VARCHAR(50)                           COMMENT '多头指数名称',
  `short_index`     VARCHAR(20)                           COMMENT '空头指数代码 (对应 index_basic)',
  `short_name`      VARCHAR(50)                           COMMENT '空头指数名称',
  `description`     VARCHAR(200)                          COMMENT '因子说明',
  `display_order`   INT           DEFAULT 999             COMMENT '展示顺序',
  `is_active`       TINYINT(1)    DEFAULT 1               COMMENT '是否启用',
  `created_at`      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`factor_code`),
  KEY `idx_active_order` (`is_active`, `display_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='DIM: 风格因子定义';

-- 初始化 4 个核心因子 (确保指数代码在 chapter1 的 index_basic 中存在)
INSERT INTO `dim_style_factor` 
  (factor_code, factor_name, long_index, long_name, short_index, short_name, description, display_order)
VALUES
  ('large_vs_small',    '大小盘',   '000300.SH',  '沪深300',   '932000.CSI', '中证2000',  '大盘 - 小盘', 1),
  ('value_vs_growth',   '价值成长', '000919.CSI', '300价值',   '000918.CSI', '300成长',   '价值 - 成长', 2),
  ('dividend_vs_micro', '红利微盘', '000922.CSI', '中证红利',   '8841431.WI', '万得微盘股', '红利 - 微盘', 3),
  ('north_vs_south',    '主板创业', '000001.SH',  '上证综指',   '399006.SZ',  '创业板指',   '上证 - 创业', 4);
```

---

## E1-S2: 行业与概念日线行情 (ODS)

**作为** 结构分析层, **我希望** 存储申万行业指数与同花顺概念板块的完整日线行情, **以便** 计算二阶动量指标。

#### 关键说明

- **数据源**: 申万行业与概念行情均由 **akshare** 提供。
- **单位统一**: 成交额 `amount` 统一入库为 **元 (Yuan)**，涨跌幅 `pct_chg` 统一为 **小数 (Decimal)**。
- **关联键**: 概念表 `concept_code` 必须与 `stock_sector_ths.id` 对齐。

#### Task: 新建 ODS 行情表

```sql
-- ============================================
-- E1-S2-T1: 申万行业指数日线 (含估值)
-- ============================================
CREATE TABLE IF NOT EXISTS `ods_sw_index_daily` (
  `trade_date`     DATE          NOT NULL,
  `ts_code`        VARCHAR(20)   NOT NULL                COMMENT '行业代码, 如 801010.SI',
  `name`           VARCHAR(50),
  `level`          VARCHAR(10)   NOT NULL                COMMENT 'l1=一级, l2=二级',
  `open`           DECIMAL(16,4),
  `high`           DECIMAL(16,4),
  `low`            DECIMAL(16,4),
  `close`          DECIMAL(16,4),
  `pre_close`      DECIMAL(16,4),
  `pct_chg`        DECIMAL(10,6)                         COMMENT '涨跌幅(小数)',
  `vol`            DECIMAL(20,2)                         COMMENT '成交量(手)',
  `amount`         DECIMAL(20,2)                         COMMENT '成交额(元)',
  `pe_ttm`         DECIMAL(12,4)                         COMMENT '滚动市盈率',
  `pb`             DECIMAL(12,4)                         COMMENT '市净率',
  `dv_ratio`       DECIMAL(10,6)                         COMMENT '股息率(小数)',
  `data_source`    VARCHAR(20)   DEFAULT 'akshare',
  `created_at`     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`trade_date`, `ts_code`),
  KEY `idx_level_date` (`level`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='ODS: 申万一级/二级行业指数日线';

-- ============================================
-- E1-S2-T2: 概念板块日线 (同花顺口径)
-- ============================================
CREATE TABLE IF NOT EXISTS `ods_concept_kline_daily` (
  `trade_date`        DATE          NOT NULL,
  `concept_code`      VARCHAR(30)   NOT NULL                COMMENT '对应 stock_sector_ths.id',
  `concept_name`      VARCHAR(80),
  `open`              DECIMAL(16,4),
  `high`              DECIMAL(16,4),
  `low`               DECIMAL(16,4),
  `close`             DECIMAL(16,4),
  `pct_chg`           DECIMAL(10,6),
  `amount`            DECIMAL(20,2)                         COMMENT '成交额(元)',
  `up_count`          INT                                   COMMENT '上涨家数',
  `down_count`        INT                                   COMMENT '下跌家数',
  `constituent_count` INT                                   COMMENT '成分股总数',
  `data_source`       VARCHAR(20)   DEFAULT 'akshare',
  `created_at`        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`trade_date`, `concept_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='ODS: 概念板块日线行情';
```

---

## E1-S3: 结构分化指标层 (ADS)

**作为** 看板数据源, **我希望** 沉淀高度聚合的 L2 指标, **以便** 实现“一秒加载”行业与风格分化图表。

#### Task: 新建 ADS 指标表

```sql
-- ============================================
-- E1-S3-T1: L2 行业指标 (申万一级)
-- ============================================
CREATE TABLE IF NOT EXISTS `ads_l2_industry_daily` (
  `trade_date`             DATE          NOT NULL,
  `industry_code`          VARCHAR(20)   NOT NULL,
  `industry_name`          VARCHAR(50),
  `close`                  DECIMAL(16,4),
  `pct_chg`                DECIMAL(10,6),
  `amount`                 DECIMAL(20,2),
  `internal_breadth`       DECIMAL(10,6)                       COMMENT '内部广度 (up/total)',
  `top_stock_code`         VARCHAR(20)                         COMMENT '领涨股代码',
  `top_stock_name`         VARCHAR(50),
  `rank_today`             INT                                 COMMENT '当日涨幅排名',
  `rank_diff_5d`           INT                                 COMMENT '5日排名变化(负数代表走强)',
  `pe_pctile_5y`           DECIMAL(10,6)                       COMMENT 'PE 5年分位',
  `heat_label`             VARCHAR(20)                         COMMENT 'hot/warm/normal/cold',
  `compute_version`        VARCHAR(20)   DEFAULT 'v1',
  `created_at`             TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`trade_date`, `industry_code`),
  KEY `idx_date_rank` (`trade_date`, `rank_today`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='ADS: 行业 L2 结构指标';

-- ============================================
-- E1-S3-T2: L2 概念指标 (同花顺概念)
-- ============================================
CREATE TABLE IF NOT EXISTS `ads_l2_concept_daily` (
  `trade_date`             DATE          NOT NULL,
  `concept_code`           VARCHAR(30)   NOT NULL,
  `concept_name`           VARCHAR(80),
  `pct_chg`                DECIMAL(10,6),
  `amount`                 DECIMAL(20,2),
  `internal_breadth`       DECIMAL(10,6),
  `limit_up_count`         INT                                 COMMENT '概念内涨停数',
  `persistence_score`      DECIMAL(10,6)                       COMMENT '持续性评分(0-1)',
  `theme_label`            VARCHAR(20)                         COMMENT 'main_theme/one_day/etc',
  `created_at`             TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`trade_date`, `concept_code`),
  KEY `idx_date_pct` (`trade_date`, `pct_chg`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='ADS: 概念 L2 结构指标';

-- ============================================
-- E1-S3-T3: L2 风格因子表现
-- ============================================
CREATE TABLE IF NOT EXISTS `ads_l2_style_factor` (
  `trade_date`         DATE          NOT NULL,
  `factor_code`        VARCHAR(30)   NOT NULL,
  `factor_name`        VARCHAR(50),
  `spread_today`       DECIMAL(10,6)                           COMMENT '多头涨幅 - 空头涨幅',
  `spread_5d`          DECIMAL(10,6)                           COMMENT '5日累计差值',
  `direction`          VARCHAR(20)                             COMMENT 'long_dominant/short_dominant',
  `created_at`         TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`trade_date`, `factor_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='ADS: 风格 L2 结构指标';
```
