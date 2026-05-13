-- E7-S2-H1: 影子审计表结构可靠性加固 (全量对账)
-- 变更内容:
--   1. 将单一 price_mae/vol_mae 拆分为 7 维全量字段 MAE
--   2. 增加异常值计数 (outlier_count)
--   3. 增加报告内容持久化字段 (report_content LONGTEXT)
--   4. 补齐审计三件套 (updated_at, is_deleted)

-- 移除旧的笼统字段
ALTER TABLE `meta_data_audit_log`
DROP COLUMN IF EXISTS `price_mae`,
DROP COLUMN IF EXISTS `vol_mae`;

-- 增加 7 维全量 MAE 字段
ALTER TABLE `meta_data_audit_log`
ADD COLUMN `open_mae` DECIMAL(10, 4) DEFAULT 0 COMMENT '开盘价平均绝对误差' AFTER `overlap_count`,
ADD COLUMN `high_mae` DECIMAL(10, 4) DEFAULT 0 COMMENT '最高价平均绝对误差' AFTER `open_mae`,
ADD COLUMN `low_mae` DECIMAL(10, 4) DEFAULT 0 COMMENT '最低价平均绝对误差' AFTER `high_mae`,
ADD COLUMN `close_mae` DECIMAL(10, 4) DEFAULT 0 COMMENT '收盘价平均绝对误差 (唯一判定字段)' AFTER `low_mae`,
ADD COLUMN `volume_mae` DECIMAL(16, 2) DEFAULT 0 COMMENT '成交量平均绝对误差(手)' AFTER `close_mae`,
ADD COLUMN `amount_mae` DECIMAL(16, 2) DEFAULT 0 COMMENT '成交额平均绝对误差(元)' AFTER `volume_mae`,
ADD COLUMN `pct_chg_mae` DECIMAL(10, 6) DEFAULT 0 COMMENT '涨跌幅平均绝对误差(小数)' AFTER `amount_mae`;

-- 增加异常值计数
ALTER TABLE `meta_data_audit_log`
ADD COLUMN `outlier_count` INT DEFAULT 0 COMMENT '收盘价偏差>1%的个股数' AFTER `pct_chg_mae`;

-- 增加报告内容持久化
ALTER TABLE `meta_data_audit_log`
ADD COLUMN `report_content` LONGTEXT COMMENT 'Markdown 报告全文' AFTER `report_path`;

-- 补齐审计三件套
ALTER TABLE `meta_data_audit_log`
ADD COLUMN `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间' AFTER `report_content`,
ADD COLUMN `is_deleted` TINYINT DEFAULT 0 COMMENT '逻辑删除' AFTER `updated_at`;
