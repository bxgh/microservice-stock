-- Migration: Create meta_sync_status table for E200-S3 Consistency
-- Created At: 2026-05-11

CREATE TABLE IF NOT EXISTS `meta_sync_status` (
    `table_name` VARCHAR(64) PRIMARY KEY COMMENT '表名',
    `last_commit_lsn` BIGINT NOT NULL DEFAULT 0 COMMENT '最后一次确认的 LSN 位点',
    `last_sync_at` DATETIME COMMENT '最后一次同步成功时间',
    `status` VARCHAR(16) DEFAULT 'NORMAL' COMMENT 'NORMAL/DELAY/ERROR',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
