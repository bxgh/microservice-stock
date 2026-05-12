-- Migration: E400 - P0 核心行情与因子采集表补全
-- Target: Tencent Cloud MySQL 5.7

-- 1. 申万行业成员维表 (拉链表)
CREATE TABLE IF NOT EXISTS `dim_sw_industry_member` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `index_code` VARCHAR(20) NOT NULL COMMENT '指数代码',
    `index_name` VARCHAR(50) DEFAULT NULL COMMENT '指数名称',
    `con_code` VARCHAR(20) NOT NULL COMMENT '成分股票代码',
    `con_name` VARCHAR(50) DEFAULT NULL COMMENT '成分股票名称',
    `in_date` DATE DEFAULT NULL COMMENT '纳入日期',
    `out_date` DATE DEFAULT NULL COMMENT '剔除日期',
    `is_new` VARCHAR(10) DEFAULT NULL COMMENT '是否最新',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT(1) DEFAULT 0,
    UNIQUE KEY `uk_index_con_date` (`index_code`, `con_code`, `in_date`),
    INDEX `idx_con_code` (`con_code`),
    INDEX `idx_in_date` (`in_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='申万行业成员拉链表';

-- 2. 补全 ods_index_daily (如果不存在)
CREATE TABLE IF NOT EXISTS `ods_index_daily` (
    `ts_code` VARCHAR(20) NOT NULL,
    `trade_date` DATE NOT NULL,
    `open` DECIMAL(16,4) DEFAULT NULL,
    `high` DECIMAL(16,4) DEFAULT NULL,
    `low` DECIMAL(16,4) DEFAULT NULL,
    `close` DECIMAL(16,4) DEFAULT NULL,
    `pre_close` DECIMAL(16,4) DEFAULT NULL,
    `change` DECIMAL(16,4) DEFAULT NULL,
    `pct_chg` DECIMAL(10,6) DEFAULT NULL,
    `vol` DECIMAL(20,2) DEFAULT NULL,
    `amount` DECIMAL(20,2) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`ts_code`, `trade_date`),
    INDEX `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='指数日线行情';

-- 3. 补全 stock_adjust_factor 字段对齐 (针对存量表)
-- 确保 adjust_factor 字段存在
-- ALTER TABLE `stock_adjust_factor` ADD COLUMN IF NOT EXISTS `adjust_factor` DECIMAL(16,6) DEFAULT NULL;
