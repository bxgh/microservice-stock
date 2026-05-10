-- 20260509_create_ods_financial_tables.sql
-- 创建符合 v1.2 规范的 ODS 层财务报表

-- 1. 资产负债表 (原始层)
CREATE TABLE IF NOT EXISTS ods_fin_balancesheet (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    ann_date DATE COMMENT '公告日期',
    f_ann_date DATE COMMENT '实际公告日期',
    end_date DATE NOT NULL COMMENT '报告期',
    report_type VARCHAR(10) COMMENT '报表类型',
    comp_type VARCHAR(10) COMMENT '公司类型',
    total_assets DECIMAL(20,4) COMMENT '资产总计',
    total_liabilities DECIMAL(20,4) COMMENT '负债合计',
    total_hldr_eqy_exc_min_int DECIMAL(20,4) COMMENT '股东权益合计(不含少数股东权益)',
    total_hldr_eqy_inc_min_int DECIMAL(20,4) COMMENT '股东权益合计(含少数股东权益)',
    monetary_funds DECIMAL(20,4) COMMENT '货币资金',
    notes_receiv DECIMAL(20,4) COMMENT '应收票据',
    accounts_receiv DECIMAL(20,4) COMMENT '应收账款',
    inventory DECIMAL(20,4) COMMENT '存货',
    goodwill DECIMAL(20,4) COMMENT '商誉',
    short_term_borrow DECIMAL(20,4) COMMENT '短期借款',
    long_term_borrow DECIMAL(20,4) COMMENT '长期借款',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) DEFAULT 0,
    UNIQUE KEY uk_code_period_type (ts_code, end_date, report_type),
    INDEX idx_end_date (end_date),
    INDEX idx_ann_date (ann_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资产负债表(ODS)';

-- 2. 利润表 (原始层)
CREATE TABLE IF NOT EXISTS ods_fin_income (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    ann_date DATE,
    f_ann_date DATE,
    end_date DATE NOT NULL,
    report_type VARCHAR(10),
    comp_type VARCHAR(10),
    basic_eps DECIMAL(10,4) COMMENT '基本每股收益',
    diluted_eps DECIMAL(10,4) COMMENT '稀释每股收益',
    total_revenue DECIMAL(20,4) COMMENT '营业总收入',
    revenue DECIMAL(20,4) COMMENT '营业收入',
    total_cogs DECIMAL(20,4) COMMENT '营业总成本',
    oper_cost DECIMAL(20,4) COMMENT '营业成本',
    sell_exp DECIMAL(20,4) COMMENT '销售费用',
    admin_exp DECIMAL(20,4) COMMENT '管理费用',
    fin_exp DECIMAL(20,4) COMMENT '财务费用',
    operate_profit DECIMAL(20,4) COMMENT '营业利润',
    total_profit DECIMAL(20,4) COMMENT '利润总额',
    net_profit DECIMAL(20,4) COMMENT '净利润',
    n_income_attr_p DECIMAL(20,4) COMMENT '归属于母公司所有者的净利润',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) DEFAULT 0,
    UNIQUE KEY uk_code_period_type (ts_code, end_date, report_type),
    INDEX idx_end_date (end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='利润表(ODS)';

-- 3. 现金流量表 (原始层)
CREATE TABLE IF NOT EXISTS ods_fin_cashflow (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    ann_date DATE,
    f_ann_date DATE,
    end_date DATE NOT NULL,
    report_type VARCHAR(10),
    comp_type VARCHAR(10),
    net_cash_flows_oper_act DECIMAL(20,4) COMMENT '经营活动产生的现金流量净额',
    net_cash_flows_inv_act DECIMAL(20,4) COMMENT '投资活动产生的现金流量净额',
    net_cash_flows_fnc_act DECIMAL(20,4) COMMENT '筹资活动产生的现金流量净额',
    free_cashflow DECIMAL(20,4) COMMENT '企业自由现金流量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) DEFAULT 0,
    UNIQUE KEY uk_code_period_type (ts_code, end_date, report_type),
    INDEX idx_end_date (end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='现金流量表(ODS)';

-- 4. 财务指标 (原始层)
CREATE TABLE IF NOT EXISTS ods_fin_indicators (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    ann_date DATE,
    end_date DATE NOT NULL,
    eps DECIMAL(10,4) COMMENT '每股收益',
    dt_eps DECIMAL(10,4) COMMENT '稀释每股收益',
    total_revenue_ps DECIMAL(20,4) COMMENT '每股营业总收入',
    revenue_ps DECIMAL(20,4) COMMENT '每股营业收入',
    capital_rese_ps DECIMAL(20,4) COMMENT '每股资本公积',
    undist_profit_ps DECIMAL(20,4) COMMENT '每股未分配利润',
    roe DECIMAL(10,4) COMMENT '净资产收益率',
    roe_dt DECIMAL(10,4) COMMENT '净资产收益率(摊薄)',
    roa DECIMAL(10,4) COMMENT '总资产报酬率',
    netprofit_margin DECIMAL(10,4) COMMENT '销售净利率',
    grossprofit_margin DECIMAL(10,4) COMMENT '销售毛利率',
    debt_to_assets DECIMAL(10,4) COMMENT '资产负债率',
    current_ratio DECIMAL(10,4) COMMENT '流动比率',
    quick_ratio DECIMAL(10,4) COMMENT '速动比率',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) DEFAULT 0,
    UNIQUE KEY uk_code_period (ts_code, end_date),
    INDEX idx_end_date (end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='财务指标(ODS)';
