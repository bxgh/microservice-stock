-- Create dq_metrics_history table for E7 Data Quality Observability
CREATE TABLE IF NOT EXISTS dq_metrics_history (
    trade_date DATE NOT NULL,
    indicator_name VARCHAR(50) NOT NULL,
    indicator_value FLOAT NOT NULL,
    target_value FLOAT DEFAULT NULL,
    status VARCHAR(20) DEFAULT 'OK',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, indicator_name),
    INDEX idx_trade_date (trade_date),
    INDEX idx_indicator_name (indicator_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
