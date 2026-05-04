-- E5: 业务规则校验维度表迁移脚本
-- 创建时间: 2026-05-05

USE stock_db;

-- 1. 股票状态维度表 (每日状态)
CREATE TABLE IF NOT EXISTS `dim_stock_status` (
    `ts_code` VARCHAR(20) NOT NULL COMMENT '股票代码 (600519.SH)',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `status` VARCHAR(20) DEFAULT 'NORMAL' COMMENT '状态: NORMAL, ST, *ST, SUSPEND, NEW, DELIST',
    `is_st` TINYINT(1) DEFAULT 0 COMMENT '是否为 ST/*ST',
    `is_suspended` TINYINT(1) DEFAULT 0 COMMENT '是否停牌',
    `is_new` TINYINT(1) DEFAULT 0 COMMENT '是否为上市 N 日内新股',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`ts_code`, `trade_date`),
    INDEX `idx_date_status` (`trade_date`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='股票每日状态维度表';

-- 2. 涨跌幅限制维度表
CREATE TABLE IF NOT EXISTS `dim_price_limit` (
    `ts_code` VARCHAR(20) NOT NULL,
    `trade_date` DATE NOT NULL,
    `up_limit_pct` DECIMAL(8, 4) NOT NULL COMMENT '理论涨停板比例 (如 0.10, 0.20)',
    `down_limit_pct` DECIMAL(8, 4) NOT NULL COMMENT '理论跌停板比例 (如 -0.10, -0.20)',
    `rule_desc` VARCHAR(100) COMMENT '规则描述 (如: 主板ST 5%)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`ts_code`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='股票每日涨跌幅限制维度表';

-- 3. 除权除息事件流水表
CREATE TABLE IF NOT EXISTS `dim_corporate_action` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ts_code` VARCHAR(20) NOT NULL,
    `ann_date` DATE COMMENT '公告日期',
    `record_date` DATE COMMENT '股权登记日',
    `ex_date` DATE NOT NULL COMMENT '除权除息日',
    `pay_date` DATE COMMENT '派息日',
    `div_cash` DECIMAL(18, 4) DEFAULT 0 COMMENT '每股分红 (税前)',
    `stk_div` DECIMAL(18, 4) DEFAULT 0 COMMENT '每股送红股',
    `stk_add` DECIMAL(18, 4) DEFAULT 0 COMMENT '每股转增股本',
    `event_type` VARCHAR(20) COMMENT '事件类型: DIVIDEND, SPLIT, ALLOTMENT',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_code_exdate` (`ts_code`, `ex_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='除权除息事件流水表';

-- 4. 证券代码变更映射表
CREATE TABLE IF NOT EXISTS `dim_code_remap` (
    `old_ts_code` VARCHAR(20) NOT NULL,
    `new_ts_code` VARCHAR(20) NOT NULL,
    `change_date` DATE NOT NULL,
    `change_reason` VARCHAR(255),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`old_ts_code`, `new_ts_code`),
    INDEX `idx_new_code` (`new_ts_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='证券代码变更映射表';
