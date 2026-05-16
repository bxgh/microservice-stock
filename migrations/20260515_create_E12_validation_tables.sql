-- Migration: E12 - 历史数据校验与自动修复体系基础表
-- Target: Tencent Cloud MySQL 5.7
-- Status: Updated to align with E12-S1 implementation plan

-- 1. 任务队列表 (用于自动修复补数)
CREATE TABLE IF NOT EXISTS `meta_task_queue` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `task_type` VARCHAR(32) NOT NULL COMMENT 'REPAIR_KLINE / REPAIR_FACTOR',
  `ts_code` VARCHAR(16) NOT NULL,
  `trade_date` DATE NOT NULL,
  `error_type` ENUM('HOLE', 'PRICE_MISMATCH', 'VOLUME_MISMATCH', 'FACTOR_STALE') NOT NULL,
  `context` JSON COMMENT '存储对账细节,如 {"local": 10.1, "target": 10.0, "source": "Tushare"}',
  `status` ENUM('PENDING', 'RUNNING', 'SUCCESS', 'FAILED') DEFAULT 'PENDING',
  `retry_count` TINYINT DEFAULT 0,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_status_type` (`status`, `task_type`),
  INDEX `idx_code_date` (`ts_code`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据修复任务队列';

-- 2. 系统配置表 (用于存储校验锚点等)
CREATE TABLE IF NOT EXISTS `meta_config` (
    `config_key` VARCHAR(100) PRIMARY KEY,
    `config_value` TEXT NOT NULL,
    `description` TEXT DEFAULT NULL,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统全局配置表';

-- 3. 修复历史存证表 (可选, 计划中未明确, 但migration中已有, 保留以备后用)
CREATE TABLE IF NOT EXISTS `meta_repair_history` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` BIGINT UNSIGNED NOT NULL,
    `ts_code` VARCHAR(20) NOT NULL,
    `trade_date` DATE NOT NULL,
    `repair_type` VARCHAR(50) NOT NULL,
    `old_value` JSON DEFAULT NULL,
    `new_value` JSON DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_ts_date` (`ts_code`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据修复历史审计';
