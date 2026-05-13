-- V1.4: 审计日志表增强 - 支持覆盖率基准比对与来源标记
-- 影响表: meta_data_audit_log

ALTER TABLE `meta_data_audit_log` 
ADD COLUMN `diff_list` LONGTEXT DEFAULT NULL COMMENT '缺失股票代码列表 (JSON)' AFTER `report_content`,
ADD COLUMN `source_tag` VARCHAR(64) DEFAULT 'TUSHARE_P0' COMMENT '最终采纳的数据源标签' AFTER `diff_list`;

-- 为 source_tag 增加索引，方便查询 fail-over 历史
ALTER TABLE `meta_data_audit_log` ADD INDEX idx_source_tag (source_tag);
