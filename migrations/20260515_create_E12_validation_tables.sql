-- Migration: E12 - 历史数据校验与自动修复体系基础表
-- Target: Tencent Cloud MySQL 5.7

-- 1. 任务队列表 (用于自动修复补数)
CREATE TABLE IF NOT EXISTS `meta_task_queue` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_type` VARCHAR(50) NOT NULL COMMENT '任务类型: kline_refetch, adj_factor_repair 等',
    `priority` INT DEFAULT 5 COMMENT '优先级: 1(高) - 10(低)',
    `params` JSON NOT NULL COMMENT '任务参数 (JSON 格式)',
    `status` ENUM('pending', 'doing', 'done', 'failed') DEFAULT 'pending',
    `error_message` TEXT DEFAULT NULL,
    `retries` INT DEFAULT 0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_status_priority` (`status`, `priority`),
    INDEX `idx_task_type` (`task_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据修复任务队列';

-- 2. 系统配置表 (用于存储校验锚点等)
CREATE TABLE IF NOT EXISTS `meta_config` (
    `config_key` VARCHAR(100) PRIMARY KEY,
    `config_value` TEXT NOT NULL,
    `description` TEXT DEFAULT NULL,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统全局配置表';

-- 3. 修复历史存证表
CREATE TABLE IF NOT EXISTS `meta_repair_history` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` BIGINT NOT NULL,
    `ts_code` VARCHAR(20) NOT NULL,
    `trade_date` DATE NOT NULL,
    `repair_type` VARCHAR(50) NOT NULL,
    `old_value` JSON DEFAULT NULL,
    `new_value` JSON DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_ts_date` (`ts_code`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据修复历史审计';
