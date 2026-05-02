-- 001_initial_tables.sql
-- 初始基础业务表

CREATE TABLE IF NOT EXISTS stock_suspensions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    trade_date DATE NOT NULL COMMENT '停牌日期',
    is_suspended TINYINT(1) DEFAULT 1 COMMENT '是否停牌 1=是',
    reason VARCHAR(255) COMMENT '停牌原因(如有)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_date (ts_code, trade_date),
    KEY idx_date (trade_date),
    KEY idx_code (ts_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票每日停牌记录';

CREATE TABLE IF NOT EXISTS stock_xr_schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    ex_date DATE NOT NULL COMMENT '除权除息日',
    bonus_ratio DECIMAL(10,4) DEFAULT 0 COMMENT '送转比例',
    cash_div DECIMAL(10,4) DEFAULT 0 COMMENT '每股派现',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_date (ts_code, ex_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='除权除息日程表';

CREATE TABLE IF NOT EXISTS stock_performance_forecast (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    report_period DATE NOT NULL COMMENT '报告期',
    notice_date DATE NOT NULL COMMENT '公告日期',
    type VARCHAR(255) COMMENT '业绩变动类型',
    growth_range VARCHAR(255) COMMENT '预告幅度',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_period (ts_code, report_period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='业绩预告表';
