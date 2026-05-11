-- Migration: Create meta_repair_whitelist table for E200-S4 Whitelist Governance
-- Created At: 2026-05-11

CREATE TABLE IF NOT EXISTS `meta_repair_whitelist` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ts_code` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `rule_id` VARCHAR(64) NOT NULL COMMENT '忽略的规则ID',
    `reason` TEXT COMMENT '加入白名单的原因',
    `expire_at` DATETIME NOT NULL COMMENT '过期时间',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT(1) DEFAULT 0 COMMENT '逻辑删除标识',
    INDEX `idx_ts_date` (`ts_code`, `trade_date`),
    INDEX `idx_expire` (`expire_at`, `is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
