-- E15-M6: 升级 meta_llm_daily_cost 增加 is_off_peak 复合主键以分立错峰记账

-- 1. 升级主键和增加 is_off_peak 列
ALTER TABLE `meta_llm_daily_cost` DROP PRIMARY KEY;
ALTER TABLE `meta_llm_daily_cost` ADD COLUMN `is_off_peak` TINYINT(1) DEFAULT 0 COMMENT '是否为错峰时段' AFTER `cost_date`;
ALTER TABLE `meta_llm_daily_cost` ADD PRIMARY KEY (`cost_date`, `is_off_peak`);
