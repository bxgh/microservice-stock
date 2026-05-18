-- V1.9: E15-M1-Patch 影子对照表与监控告警前置 DDL

-- 1. 创建 dwd_policy_analysis_shadow 影子对照表
-- 结构必须与主表 dwd_policy_analysis 100% 一致，用于安全承接 Rule-Based 引擎的旁路双写测试
CREATE TABLE IF NOT EXISTS `dwd_policy_analysis_shadow` LIKE `dwd_policy_analysis`;

-- 2. （可选）为后续监控增加索引支持
ALTER TABLE `dwd_policy_analysis` ADD INDEX `idx_created_at_analysis_path` (`created_at`, `analysis_path`);
