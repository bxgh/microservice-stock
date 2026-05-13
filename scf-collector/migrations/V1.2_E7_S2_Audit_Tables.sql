-- E7-S2: 影子审计与校验证据表
CREATE TABLE IF NOT EXISTS `meta_data_audit_log` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `trade_date` VARCHAR(10) NOT NULL COMMENT '对账日期',
    `primary_source` VARCHAR(20) DEFAULT 'Tushare' COMMENT '主数据源',
    `secondary_source` VARCHAR(20) DEFAULT 'AkShare' COMMENT '备份数据源',
    `primary_count` INT DEFAULT 0 COMMENT '主源股票数',
    `secondary_count` INT DEFAULT 0 COMMENT '备份源股票数',
    `overlap_count` INT DEFAULT 0 COMMENT '重叠股票数',
    `price_mae` DECIMAL(10, 6) DEFAULT 0 COMMENT '价格平均绝对误差',
    `vol_mae` DECIMAL(10, 2) DEFAULT 0 COMMENT '成交量平均绝对误差(手)',
    `status` VARCHAR(20) DEFAULT 'PASS' COMMENT '对账状态: PASS, WARNING, FAIL',
    `report_path` VARCHAR(255) DEFAULT '' COMMENT 'Markdown 报告路径',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
