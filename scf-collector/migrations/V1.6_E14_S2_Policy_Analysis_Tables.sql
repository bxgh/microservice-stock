-- Migration: V1.6_E14_S2_Policy_Analysis_Tables
-- Description: Alter ods_policy_info & Create dwd_policy_analysis & meta_llm_daily_cost
-- Created At: 2026-05-17

-- 1. 扩展原始政策信息表，添加 policy_type 和 analysis_status 字段及索引
ALTER TABLE `ods_policy_info` 
    ADD COLUMN `policy_type` VARCHAR(50) DEFAULT 'other' COMMENT '政策分类，关联 dim_policy_type' AFTER `ts_code`,
    ADD COLUMN `analysis_status` VARCHAR(20) DEFAULT 'pending_analysis' COMMENT 'AI分析状态' AFTER `content_md5`,
    ADD INDEX `idx_analysis_status` (`analysis_status`),
    ADD INDEX `idx_policy_type` (`policy_type`);

-- 2. 新建 AI 分析明细表 dwd_policy_analysis
CREATE TABLE IF NOT EXISTS `dwd_policy_analysis` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `policy_id` INT NOT NULL COMMENT '关联 ods_policy_info.id',
    
    -- AI 核心摘要成果
    `summary` VARCHAR(1500) NOT NULL COMMENT 'AI 三句话摘要 (JSON数组)',
    `importance_level` TINYINT COMMENT '重要性评级 1-5',
    `importance_reason` VARCHAR(500) COMMENT '评级理由',
    `sectors_positive` MEDIUMTEXT COMMENT '受益板块及标的 (JSON)',
    `sectors_negative` MEDIUMTEXT COMMENT '受损板块 (JSON)',
    
    -- 措辞对比
    `intensity_change` VARCHAR(20) DEFAULT 'N/A' COMMENT '强度变化：增强/持平/减弱/不适用',
    `key_differences` MEDIUMTEXT COMMENT '措辞文字差异详情 (JSON)',
    `implication` VARCHAR(1000) COMMENT '市场隐含影响说明',
    `contrast_baseline_id` INT DEFAULT NULL COMMENT '对比基准政策 id',
    `segment_used` MEDIUMTEXT COMMENT '实际截取用于分析的段落',
    `segment_extracted` TINYINT(1) DEFAULT 1 COMMENT '关键段落是否提取成功',
    `input_truncated` TINYINT(1) DEFAULT 0 COMMENT '输入是否被物理截断',
    
    -- MLOps 追踪
    `prompt_name` VARCHAR(50) NOT NULL COMMENT 'Prompt 分类',
    `prompt_version` VARCHAR(10) NOT NULL COMMENT 'Prompt 版本',
    `model_name` VARCHAR(50) NOT NULL COMMENT '使用的物理模型名',
    `thinking_enabled` TINYINT(1) DEFAULT 0 COMMENT '是否启用 thinking',
    `reasoning_effort` VARCHAR(10) DEFAULT NULL COMMENT '思考档位 low/medium/high',
    
    -- Token 消耗与计费 (6位小数)
    `input_cache_hit_tokens` INT DEFAULT 0 COMMENT '缓存命中输入 token',
    `input_cache_miss_tokens` INT DEFAULT 0 COMMENT '缓存未命中输入 token',
    `output_tokens` INT DEFAULT 0 COMMENT '输出 token',
    `reasoning_tokens` INT DEFAULT 0 COMMENT '深度思考 token',
    `cost_cny` DECIMAL(10,6) DEFAULT 0.000000 COMMENT '单次调用实际成本 (CNY)',
    
    -- 调试与错误诊断
    `raw_response` MEDIUMTEXT COMMENT 'LLM 原始返回 (异常排查)',
    `reasoning_content` MEDIUMTEXT COMMENT '思考链中间输出',
    `analysis_duration_ms` INT DEFAULT 0 COMMENT '调用耗时 (ms)',
    
    -- 状态与重试
    `analysis_status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '处理状态',
    `error_message` VARCHAR(500) DEFAULT NULL COMMENT '错误报错描述',
    `retry_count` TINYINT DEFAULT 0 COMMENT '重试次数',
    
    -- DDL 三件套
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT(1) DEFAULT 0,
    
    UNIQUE KEY `uk_policy_prompt` (`policy_id`, `prompt_name`, `prompt_version`),
    KEY `idx_intensity_change` (`intensity_change`),
    KEY `idx_importance_level` (`importance_level`),
    KEY `idx_analysis_status` (`analysis_status`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='政策 AI 分析明细';

-- 3. 新建大模型日消费累计审计表 meta_llm_daily_cost
CREATE TABLE IF NOT EXISTS `meta_llm_daily_cost` (
    `cost_date` DATE PRIMARY KEY,
    `total_cost_cny` DECIMAL(10,6) DEFAULT 0.000000,
    `total_calls` INT DEFAULT 0,
    `total_input_tokens` BIGINT DEFAULT 0,
    `total_output_tokens` BIGINT DEFAULT 0,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='LLM 日累计成本审计表';
