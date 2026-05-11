# 附录 A: 核心数据表 DDL 示意

> 完整 DDL 见 `db/init_schema.sql`,本文档仅列出关键表结构骨架。

```sql
-- 行情日数据(双写到 MySQL 和 ClickHouse)
CREATE TABLE ods_quotes_daily (
    ts_code VARCHAR(10) NOT NULL COMMENT '股票代码,含 .SH/.SZ/.BJ',
    trade_date DATE NOT NULL COMMENT '交易日期',
    open DECIMAL(20,4) COMMENT '开盘价(元)',
    high DECIMAL(20,4),
    low DECIMAL(20,4),
    close DECIMAL(20,4),
    pre_close DECIMAL(20,4),
    vol BIGINT COMMENT '成交量(股)',
    amount DECIMAL(20,4) COMMENT '成交额(元)',
    turnover_rate DECIMAL(8,4) COMMENT '换手率(%)',
    pe_ttm DECIMAL(20,4),
    pb DECIMAL(20,4),
    total_mv DECIMAL(20,4) COMMENT '总市值(万元)',
    circ_mv DECIMAL(20,4) COMMENT '流通市值(万元)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) DEFAULT 0,
    PRIMARY KEY (ts_code, trade_date),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB COMMENT '日行情';

-- 资产负债表 (原始层)
CREATE TABLE ods_fin_balancesheet (
    ts_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    notice_date DATE,
    total_assets DECIMAL(20,4),
    total_liabilities DECIMAL(20,4),
    total_equity DECIMAL(20,4),
    monetary_funds DECIMAL(20,4),
    accounts_receivable DECIMAL(20,4),
    inventory DECIMAL(20,4),
    goodwill DECIMAL(20,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) DEFAULT 0,
    PRIMARY KEY (ts_code, report_date),
    INDEX idx_report_date (report_date)
) ENGINE=InnoDB COMMENT '资产负债表';

-- 利润表 (原始层)
CREATE TABLE ods_fin_income (
    ts_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    notice_date DATE,
    total_revenue DECIMAL(20,4),
    operating_cost DECIMAL(20,4),
    net_profit DECIMAL(20,4),
    parent_net_profit DECIMAL(20,4),
    research_expenses DECIMAL(20,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) DEFAULT 0,
    PRIMARY KEY (ts_code, report_date)
) ENGINE=InnoDB COMMENT '利润表';

-- 现金流量表 (原始层)
CREATE TABLE ods_fin_cashflow (
    ts_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    notice_date DATE,
    net_operating_cash_flow DECIMAL(20,4),
    net_investing_cash_flow DECIMAL(20,4),
    net_financing_cash_flow DECIMAL(20,4),
    free_cash_flow DECIMAL(20,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) DEFAULT 0,
    PRIMARY KEY (ts_code, report_date)
) ENGINE=InnoDB COMMENT '现金流量表';

-- 排雷指标(应用层)
CREATE TABLE ads_landmine_indicators (
    ts_code VARCHAR(10) NOT NULL,
    snap_date DATE NOT NULL,
    goodwill_ratio DECIMAL(8,4) COMMENT '商誉/净资产',
    cfo_ni_ratio_3yr DECIMAL(8,4) COMMENT '经营现金流/净利润 3 年均值',
    receivable_days_change DECIMAL(8,4) COMMENT '应收周转天数 YoY 变化',
    pledge_ratio DECIMAL(8,4) COMMENT '大股东质押比例',
    audit_opinion VARCHAR(20) COMMENT '审计意见',
    is_st BOOLEAN COMMENT '是否 ST',
    is_landmine BOOLEAN COMMENT '是否触发排雷',
    landmine_reasons JSON COMMENT '触发原因列表',
    PRIMARY KEY (ts_code, snap_date)
) ENGINE=InnoDB COMMENT '排雷指标快照';

-- AI 抽取结果(应用层 - 原始层,事实源)
CREATE TABLE ads_extracted_facts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(10) NOT NULL,
    report_period VARCHAR(10) NOT NULL COMMENT '如 2024A、2024Q3',
    schema_version VARCHAR(10) NOT NULL,
    facts_json JSON COMMENT '抽取的结构化字段(含 source_quote 溯源)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ts_period (ts_code, report_period, schema_version)
) ENGINE=InnoDB COMMENT 'AI 抽取结果(原始层)';

-- 公司指标宽表(应用层 - 消费层,从 ads_extracted_facts 同步)
CREATE TABLE ads_company_metrics (
    ts_code VARCHAR(10) NOT NULL,
    report_period VARCHAR(10) NOT NULL,
    schema_version VARCHAR(10) NOT NULL,
    -- 业务结构
    main_product VARCHAR(200) COMMENT '主营产品',
    main_revenue_share DECIMAL(8,4) COMMENT '主营营收占比',
    main_yoy_growth DECIMAL(8,4) COMMENT '主营营收同比',
    main_gross_margin DECIMAL(8,4) COMMENT '主营毛利率',
    -- 客户结构
    top5_customer_share DECIMAL(8,4) COMMENT '前五大客户占比',
    top1_customer_share DECIMAL(8,4) COMMENT '第一大客户占比',
    has_related_customer BOOLEAN COMMENT '是否含关联方客户',
    -- 研发投入
    rd_amount DECIMAL(20,4) COMMENT '研发金额(万元)',
    rd_to_revenue DECIMAL(8,4) COMMENT '研发占营收比',
    rd_capitalization_ratio DECIMAL(8,4) COMMENT '研发资本化率',
    rd_personnel INT COMMENT '研发人员数量',
    -- 政策依赖
    subsidy_amount DECIMAL(20,4) COMMENT '政府补助(万元)',
    subsidy_to_profit DECIMAL(8,4) COMMENT '补助/净利润',
    has_tax_preference BOOLEAN COMMENT '税收优惠',
    -- 财务质量(从 Tushare 计算 + 抽取交叉,这里冗余存便于查询)
    gross_margin DECIMAL(8,4),
    net_margin DECIMAL(8,4),
    roic DECIMAL(8,4),
    roe DECIMAL(8,4),
    cfo_ni_ratio DECIMAL(8,4) COMMENT '经营现金流/净利润',
    receivable_days DECIMAL(8,2) COMMENT '应收账款周转天数',
    -- 行业内分位(从 ads_industry_percentile 同步,展平到这里便于直接查)
    rd_to_revenue_pct DECIMAL(8,4) COMMENT '研发占比行业分位',
    gross_margin_pct DECIMAL(8,4) COMMENT '毛利率行业分位',
    roic_pct DECIMAL(8,4) COMMENT 'ROIC 行业分位',
    -- 产品关联(v0.3,E5-S4 引入,可选)
    primary_product_id VARCHAR(20) COMMENT '主产品 ID,关联 dim_product_mapping',
    -- 同步元数据
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '从原始层同步的时间',
    PRIMARY KEY (ts_code, report_period),
    INDEX idx_period_industry (report_period),
    INDEX idx_rd_ratio (rd_to_revenue),
    INDEX idx_product (primary_product_id),
    INDEX idx_synced_at (synced_at)
) ENGINE=InnoDB COMMENT '公司指标宽表(消费层)';

-- 补充:行业内分位单独表(便于跨公司、跨指标聚合)
CREATE TABLE ads_industry_percentile (
    ts_code VARCHAR(10) NOT NULL,
    report_period VARCHAR(10) NOT NULL,
    industry_code VARCHAR(20) NOT NULL COMMENT '申万二级或自定义概念',
    metric_name VARCHAR(40) NOT NULL COMMENT '如 rd_to_revenue, gross_margin',
    metric_value DECIMAL(20,4),
    industry_rank INT COMMENT '行业内排名',
    industry_total INT COMMENT '行业内可比公司数',
    percentile DECIMAL(8,4) COMMENT '分位 0-1',
    PRIMARY KEY (ts_code, report_period, industry_code, metric_name),
    INDEX idx_industry_metric (industry_code, metric_name, percentile)
) ENGINE=InnoDB COMMENT '行业内分位';

-- 产品 mapping 库(v0.3,E5-S4 引入,MVP 后增量)
-- 存量基准库,手工维护为主 + AI 辅助更新建议
CREATE TABLE dim_product_mapping (
    product_id VARCHAR(20) PRIMARY KEY COMMENT '产品 ID,如 SEMI-EQ-ETCH-014',
    product_name VARCHAR(200) NOT NULL COMMENT '产品名称',
    industry_node VARCHAR(100) NOT NULL COMMENT '产业链环节,如 半导体设备/前道',
    tech_generation VARCHAR(100) COMMENT '技术代际,如 14nm 及以下',
    domestic_replacement_status ENUM('imported','replacing_early','replacing_mid','replaced') 
        COMMENT '国产替代进度',
    domestic_replacement_pct DECIMAL(8,4) COMMENT '国产化率(%)',
    global_players JSON COMMENT '全球主要玩家与份额,如 [{"name":"AMAT","share":0.45}]',
    domestic_players JSON COMMENT '国产玩家与份额',
    upstream_products JSON COMMENT '上游依赖产品 ID 列表',
    downstream_application VARCHAR(500) COMMENT '下游应用',
    notes TEXT COMMENT '维护备注、关键事件',
    last_review_date DATE COMMENT '最近一次 review 日期',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_industry_node (industry_node),
    INDEX idx_replacement (domestic_replacement_status)
) ENGINE=InnoDB COMMENT '产品 mapping 库(手工维护 + AI 辅助)';

-- 产品 mapping 更新建议(AI 辅助,人工合入)
CREATE TABLE obs_product_mapping_suggestions (
    suggestion_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(20) COMMENT '关联产品 ID(若涉及新建产品则为 NULL)',
    suggestion_type ENUM('new_product','update_field','update_player','update_status') NOT NULL,
    suggested_change JSON COMMENT '建议的具体变更内容',
    source_type VARCHAR(40) COMMENT '来源类型:research_report / disclosure / news',
    source_ref VARCHAR(500) COMMENT '来源链接或文档 ID',
    source_quote TEXT COMMENT '原文引用',
    confidence DECIMAL(4,2) COMMENT 'AI 置信度 0-1',
    review_status ENUM('pending','approved','rejected') DEFAULT 'pending',
    reviewed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_review_status (review_status),
    INDEX idx_product (product_id)
) ENGINE=InnoDB COMMENT '产品 mapping 更新建议(待审)';

-- 抽取任务表(元数据)
CREATE TABLE meta_extract_tasks (
    task_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(10) NOT NULL,
    report_period VARCHAR(10) NOT NULL,
    status ENUM('pending','processing','completed','failed') NOT NULL,
    retry_count INT DEFAULT 0,
    cost_tokens INT DEFAULT 0,
    error_msg TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT '抽取任务管理';

-- 触发事件表
CREATE TABLE meta_trigger_events (
    event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(10) NOT NULL,
    event_type VARCHAR(40) NOT NULL COMMENT '如 annual_report, quarterly_report, price_anomaly',
    priority ENUM('high','medium','low') NOT NULL,
    event_payload JSON,
    status ENUM('pending','processing','completed','dropped') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status_priority (status, priority)
) ENGINE=InnoDB COMMENT '触发事件';
```

---

# 附录 B: 项目目录结构

```
astock-fundamental-system/
├── docker-compose.yml
├── config/
│   ├── landmine_rules.yaml
│   ├── financial_rules.yaml
│   ├── industry_indicators.yaml
│   └── settings.yaml
├── src/
│   ├── data/                # E1
│   │   ├── tushare_client.py
│   │   ├── akshare_client.py
│   │   ├── disclosure_crawler.py
│   │   └── daily_sync.py
│   ├── landmine/            # E2
│   │   └── compute_indicators.py
│   ├── extract/             # E3
│   │   ├── preprocess.py
│   │   ├── extractor.py
│   │   ├── schema.py
│   │   └── validator.py
│   ├── financial/           # E4
│   │   ├── rules_engine.py
│   │   └── risk_card.py
│   ├── peer/                # E5
│   │   └── industry_rank.py
│   ├── tracking/            # E6
│   │   ├── triggers.py
│   │   └── worker.py
│   ├── output/              # E7
│   │   ├── card_generator.py
│   │   └── industry_map.py
│   └── ops/                 # E8
│       ├── scheduler.py
│       └── monitor.py
├── db/
│   ├── init_schema.sql
│   └── migrations/
├── data/
│   ├── disclosures/         # 公告 PDF + Markdown
│   ├── risk_cards/
│   └── reports/
├── logs/
├── tests/
└── README.md
```
