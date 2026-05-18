-- E15: AI 政策分析引擎效率与成本优化迁移脚本 (v1.1)

-- 1. 扩展 dwd_policy_analysis 表，增加 triage 分流、缓存匹配、投票审计及错峰标记字段
ALTER TABLE dwd_policy_analysis 
    ADD COLUMN analysis_path VARCHAR(20) DEFAULT 'llm' COMMENT '分析路径: llm/rule/rule_then_llm/cache' AFTER policy_id,
    ADD COLUMN analysis_stage VARCHAR(20) DEFAULT 'triage_only' COMMENT '分析阶段: triage_only/triage_and_deep/triage_and_voting' AFTER analysis_path,
    ADD COLUMN triage_confidence DECIMAL(3,2) DEFAULT 1.00 COMMENT '初筛置信度' AFTER analysis_stage,
    ADD COLUMN triage_borderline TINYINT(1) DEFAULT 0 COMMENT '是否因置信度不足强制升级' AFTER triage_confidence,
    ADD COLUMN requires_human_review TINYINT(1) DEFAULT 0 COMMENT '是否需要人工复核' AFTER error_message,
    ADD COLUMN voting_consistency_rate DECIMAL(5,4) DEFAULT 1.0000 COMMENT '投票一致率' AFTER requires_human_review,
    ADD COLUMN core_segment_simhash CHAR(16) DEFAULT NULL COMMENT '核心段落 simhash (E6用)' AFTER voting_consistency_rate,
    ADD COLUMN is_off_peak TINYINT(1) DEFAULT 0 COMMENT '是否为错峰时段调用' AFTER cost_cny;

-- 2. 创建响应缓存表 meta_response_cache 用于阻止重复计费
CREATE TABLE IF NOT EXISTS `meta_response_cache` (
    `cache_key` CHAR(32) PRIMARY KEY COMMENT 'MD5(prompt_name+prompt_version+model+content_normalized)',
    `prompt_name` VARCHAR(50) NOT NULL,
    `prompt_version` VARCHAR(10) NOT NULL,
    `model_name` VARCHAR(50) NOT NULL,
    `response_content` MEDIUMTEXT NOT NULL COMMENT '缓存的JSON响应',
    `hit_count` INT DEFAULT 0 COMMENT '命中次数',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `last_hit_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY `idx_last_hit` (`last_hit_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='应用层LLM响应缓存表';
