-- Chapter 2: 结构分化与行业轮动相关表结构

-- 1. 申万行业日线 ODS 表 (原始数据层)
CREATE TABLE IF NOT EXISTS `ods_sw_index_daily` (
    `trade_date` DATE NOT NULL,
    `ts_code` VARCHAR(20) NOT NULL,
    `name` VARCHAR(50),
    `level` VARCHAR(10) COMMENT 'l1/l2',
    `close` DECIMAL(16,4),
    `pct_chg` DECIMAL(8,4),
    `vol` DECIMAL(20,4),
    `amount` DECIMAL(20,4),
    `pe_ttm` DECIMAL(10,4),
    `pb` DECIMAL(10,4),
    `dv_ratio` DECIMAL(10,4),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`, `ts_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 同花顺概念板块日线 ODS 表
CREATE TABLE IF NOT EXISTS `ods_concept_kline_daily` (
    `trade_date` DATE NOT NULL,
    `concept_code` VARCHAR(20) NOT NULL,
    `concept_name` VARCHAR(100),
    `open` DECIMAL(16,4),
    `high` DECIMAL(16,4),
    `low` DECIMAL(16,4),
    `close` DECIMAL(16,4),
    `pct_chg` DECIMAL(8,4),
    `amount` DECIMAL(20,4),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`, `concept_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 行业轮动分析 ADS 表 (应用层)
CREATE TABLE IF NOT EXISTS `ads_l2_industry_rotation` (
    `trade_date` DATE NOT NULL,
    `name` VARCHAR(50) NOT NULL,
    `pct_chg` DECIMAL(8,4),
    `rank_current` INT,
    `rank_5d_change` INT,
    `leader_stock` VARCHAR(50),
    `pe_percentile` DECIMAL(8,4),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`, `name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 概念轮动分析 ADS 表
CREATE TABLE IF NOT EXISTS `ads_l2_concept_rotation` (
    `trade_date` DATE NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `pct_chg` DECIMAL(8,4),
    `rank_current` INT,
    `rank_5d_change` INT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`, `name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 风格轮动分析 ADS 表
CREATE TABLE IF NOT EXISTS `ads_l2_style_rotation` (
    `trade_date` DATE NOT NULL,
    `name` VARCHAR(50) NOT NULL,
    `pct_chg` DECIMAL(8,4),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`, `name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. L2 结构全景快照表 (用于前端看板一键加载)
CREATE TABLE IF NOT EXISTS `ads_l2_structural_snapshot` (
    `trade_date` DATE NOT NULL,
    `snapshot_payload` JSON COMMENT '包含行业、概念、风格的完整JSON',
    `summary_text` TEXT COMMENT '预留的文字复盘点评',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
