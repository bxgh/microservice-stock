-- Migration: V2.0_E15_M6_Off_Peak_Daily_Cost
-- Description: Alter meta_llm_daily_cost to support off-peak split aggregation via composite primary key
-- Created At: 2026-05-18

-- 1. 修改 meta_llm_daily_cost 主键，增加 is_off_peak 区分错峰账单
ALTER TABLE `meta_llm_daily_cost` DROP PRIMARY KEY;
ALTER TABLE `meta_llm_daily_cost` ADD COLUMN `is_off_peak` TINYINT(1) DEFAULT 0 COMMENT '是否为错峰时段' AFTER `cost_date`;
ALTER TABLE `meta_llm_daily_cost` ADD PRIMARY KEY (`cost_date`, `is_off_peak`);
