# Stock-Serverless-Collector 数据库 Schema 设计

## 1. 设计原则
- **审计先行**: 每一条数据必须可追溯到具体的采集任务 ID。
- **状态驱动**: 使用状态表控制采集频率，避免 SCF 重复触发。
- **字段规范**: 严格遵守 `ts_code`, `trade_date` 命名及 `is_deleted` 逻辑删除规范。

## 2. 系统元数据表 (Meta Tables)

### 2.1 采集任务流水表 `meta_collection_tasks`
记录 SCF 每次运行的详细情况。
```sql
CREATE TABLE `meta_collection_tasks` (
  `id`              BIGINT AUTO_INCREMENT PRIMARY KEY,
  `task_name`       VARCHAR(64)  NOT NULL COMMENT '任务名称: data_hub / pywencai',
  `request_id`      VARCHAR(64)  NOT NULL COMMENT 'SCF Request ID',
  `status`          ENUM('running', 'success', 'failed') DEFAULT 'running',
  `start_time`      DATETIME     DEFAULT CURRENT_TIMESTAMP,
  `end_time`        DATETIME     NULL,
  `error_msg`       TEXT         NULL,
  `affected_rows`   INT          DEFAULT 0,
  INDEX idx_task_date (`start_time`, `task_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采集任务审计表';
```

### 2.2 数据就绪状态表 `meta_data_readiness`
记录上游数据源的就绪情况。
```sql
CREATE TABLE `meta_data_readiness` (
  `trade_date`      DATE         NOT NULL PRIMARY KEY,
  `source_name`     VARCHAR(32)  NOT NULL COMMENT 'tushare / akshare / baostock',
  `data_type`       VARCHAR(32)  NOT NULL COMMENT 'kline / finance / lhb',
  `is_ready`        TINYINT(1)   DEFAULT 0,
  `last_check_at`   DATETIME     DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_date_source (`trade_date`, `source_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据源就绪探测表';
```

## 3. 原始数据层 (ODS Tables)

### 3.1 每日行情表 `ods_stock_daily_hloc`
```sql
CREATE TABLE `ods_stock_daily_hloc` (
  `ts_code`         VARCHAR(20)  NOT NULL,
  `trade_date`      DATE         NOT NULL,
  `open`            DECIMAL(10,4),
  `high`            DECIMAL(10,4),
  `low`             DECIMAL(10,4),
  `close`           DECIMAL(10,4),
  `pre_close`       DECIMAL(10,4),
  `change`          DECIMAL(10,4),
  `pct_chg`         DECIMAL(10,6) COMMENT '涨跌幅(小数形式)',
  `vol`             DECIMAL(20,4) COMMENT '成交量(手)',
  `amount`          DECIMAL(20,4) COMMENT '成交额(千元)',
  `task_id`         BIGINT        COMMENT '关联 meta_collection_tasks',
  `created_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`      TINYINT(1)    DEFAULT 0,
  PRIMARY KEY (`ts_code`, `trade_date`),
  INDEX idx_trade_date (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日线K线表';
```

## 4. 应用数据层 (ADS Tables)

### 4.1 异动选股结果表 `ads_stock_anomalies`
存储从 PyWencai 或计算逻辑得出的异动结果。
```sql
CREATE TABLE `ads_stock_anomalies` (
  `id`              BIGINT AUTO_INCREMENT PRIMARY KEY,
  `trade_date`      DATE         NOT NULL,
  `ts_code`         VARCHAR(20)  NOT NULL,
  `stock_name`      VARCHAR(32),
  `anomaly_type`    VARCHAR(64)  COMMENT '涨停 / 缩量 / 资金大幅流入',
  `reason`          TEXT         COMMENT '异动原因/问财原始描述',
  `score`           INT          DEFAULT 0 COMMENT '推荐分值',
  `created_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`trade_date`, `ts_code`, `anomaly_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='异动股应用表';
```

---
*Created by Antigravity AI - 2026-05-11*
