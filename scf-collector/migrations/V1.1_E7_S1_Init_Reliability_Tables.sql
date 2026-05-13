-- [E7-S1] 基础设施表：停牌数据与基准快照
-- 目标库: alwaysup (MySQL 5.7)

CREATE TABLE IF NOT EXISTS `ods_suspend_d` (
  `ts_code` varchar(20) NOT NULL COMMENT 'TS代码',
  `trade_date` date NOT NULL COMMENT '交易日/停牌日',
  `suspend_timing` varchar(20) DEFAULT NULL COMMENT '停牌时段',
  `suspend_type` varchar(20) DEFAULT NULL COMMENT '停牌类型',
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`ts_code`, `trade_date`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日停牌信息原始表';

CREATE TABLE IF NOT EXISTS `meta_universe_snapshot` (
  `biz_date` date NOT NULL COMMENT '业务日期',
  `expected_count` int(11) NOT NULL COMMENT '理论应采总数',
  `codes_json` MEDIUMTEXT NOT NULL COMMENT '代码清单JSON',
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`biz_date`),
  KEY `idx_updated_at` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日采集基准快照表';
