-- Migration: Create meta_repair_log table for E200-S2 Healer engine
-- Created At: 2026-05-10

CREATE TABLE IF NOT EXISTS `meta_repair_log` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `finding_id` INT NOT NULL COMMENT '关联的 dq_findings ID',
    `ts_code` VARCHAR(20) COMMENT '股票代码',
    `trade_date` DATE COMMENT '交易日期',
    `table_name` VARCHAR(64) NOT NULL COMMENT '被修复的表名',
    `repair_type` VARCHAR(32) NOT NULL DEFAULT 'CONSENSUS' COMMENT '修复类型: CONSENSUS/MANUAL',
    `source_used` VARCHAR(32) NOT NULL COMMENT '使用的修复源: MOOTDX/AKSHARE/TUSHARE',
    `before_snapshot` JSON COMMENT '修复前数据快照',
    `after_snapshot` JSON COMMENT '修复后数据快照',
    `status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/SUCCESS/FAILED/ROLLED_BACK',
    `error_msg` TEXT COMMENT '修复失败时的错误信息',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT(1) DEFAULT 0,
    INDEX `idx_finding_id` (`finding_id`),
    INDEX `idx_ts_code_date` (`ts_code`, `trade_date`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
