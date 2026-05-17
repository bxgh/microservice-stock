-- Migration: V1.5_E14_S1_Policy_Info_Tables
-- Description: Create ods_policy_info for E14 Policy Tracking System
-- Created At: 2026-05-16

CREATE TABLE IF NOT EXISTS `ods_policy_info` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ts_code` VARCHAR(20) NOT NULL COMMENT '来源机构标识 (GOV_CN, PBC, CSRC)',
    `title` VARCHAR(255) NOT NULL COMMENT '政策标题',
    `publish_date` DATE NOT NULL COMMENT '发布日期',
    `source_url` VARCHAR(500) NOT NULL COMMENT '原文链接',
    `content_text` LONGTEXT COMMENT '提取后的干净正文内容',
    `content_md5` VARCHAR(32) NOT NULL COMMENT '内容指纹 (用于内容级去重)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT(1) DEFAULT 0,
    UNIQUE KEY `uk_source_url` (`source_url`),
    UNIQUE KEY `uk_content_md5` (`content_md5`),
    INDEX `idx_publish_date` (`publish_date`),
    INDEX `idx_ts_code` (`ts_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
