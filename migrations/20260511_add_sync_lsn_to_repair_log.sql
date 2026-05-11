-- Migration: Add sync_lsn and sync_status to meta_repair_log for E200-S3
-- Created At: 2026-05-11

ALTER TABLE `meta_repair_log` 
ADD COLUMN `sync_lsn` BIGINT DEFAULT 0 COMMENT '同步确认位点',
ADD COLUMN `sync_status` VARCHAR(16) DEFAULT 'PENDING' COMMENT 'PENDING/ACKED/ORPHAN/SKIPPED';
