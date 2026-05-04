-- E2: Create staging_rejected table for data validation auditing
CREATE TABLE IF NOT EXISTS staging_rejected (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    source_table VARCHAR(64) NOT NULL COMMENT '目标表名',
    raw_data JSON NOT NULL COMMENT '原始输入数据',
    reject_reason VARCHAR(255) NOT NULL COMMENT '失败原因',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date (trade_date),
    INDEX idx_code_date (ts_code, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
