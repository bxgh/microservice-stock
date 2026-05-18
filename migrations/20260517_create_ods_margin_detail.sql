-- Migration: Create ods_margin_detail table
-- Date: 2026-05-17
-- Epic: E13 Story: S5

CREATE TABLE IF NOT EXISTS ods_margin_detail (
    ts_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    trade_date DATE NOT NULL COMMENT '交易日期',
    name VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    rzye DECIMAL(20,2) DEFAULT NULL COMMENT '融资余额(元)',
    rzmre DECIMAL(20,2) DEFAULT NULL COMMENT '融资买入额(元)',
    rzche DECIMAL(20,2) DEFAULT NULL COMMENT '融资偿还额(元)',
    rqye DECIMAL(20,2) DEFAULT NULL COMMENT '融券余额(元)',
    rqyl DECIMAL(20,2) DEFAULT NULL COMMENT '融券余量(股)',
    rqchl DECIMAL(20,2) DEFAULT NULL COMMENT '融券偿还量(股)',
    rqmcl DECIMAL(20,2) DEFAULT NULL COMMENT '融券卖出量(股)',
    rzrqye DECIMAL(20,2) DEFAULT NULL COMMENT '融资融券余额(元)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除',
    PRIMARY KEY (ts_code, trade_date),
    KEY idx_trade_date (trade_date),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='融资融券个股每日明细';
