## E1 · 数据结构

### E1-S1 派生指标层 (ads_stock_derived_metrics)

独立派生指标层,计算一次复用 N 次,降低判定逻辑 SQL 复杂度。

```sql
CREATE TABLE `ads_stock_derived_metrics` (
  `trade_date`            DATE         NOT NULL                  COMMENT '交易日',
  `ts_code`               VARCHAR(20)  NOT NULL                  COMMENT '股票代码',
  -- 量能派生
  `volume_ratio_5d`       DECIMAL(10,4)                          COMMENT '5 日量比均值',
  `volume_ratio_20d`      DECIMAL(10,4)                          COMMENT '20 日量比均值',
  `vol_5d_to_60d`         DECIMAL(10,4)                          COMMENT '5 日均量 / 60 日均量',
  `vol_consistency_days`  TINYINT                                COMMENT '连续满足量比 ∈ [1.5,2.5] 的天数',
  -- 涨跌幅派生
  `cumulative_5d_pct`     DECIMAL(10,6)                          COMMENT '5 日累计涨跌幅',
  `cumulative_20d_pct`    DECIMAL(10,6)                          COMMENT '20 日累计涨跌幅',
  `cumulative_60d_pct`    DECIMAL(10,6)                          COMMENT '60 日累计涨跌幅',
  `amplitude_today`       DECIMAL(10,6)                          COMMENT '当日振幅',
  `amplitude_10d`         DECIMAL(10,6)                          COMMENT '10 日总振幅',
  -- 排名派生
  `industry_rank_pct_today`    DECIMAL(6,4)                      COMMENT '行业内涨幅分位(0=最强)',
  `industry_rank_pct_avg_5d`   DECIMAL(6,4)                      COMMENT '前 5 日行业内分位均值',
  `capital_rank_today`         INT                               COMMENT '主力净流入全市场排名',
  `capital_rank_avg_5d`        DECIMAL(8,2)                      COMMENT '前 5 日主力排名均值',
  -- 均线派生
  `dist_to_ma5`           DECIMAL(10,6)                          COMMENT '与 MA5 的乖离率',
  `dist_to_ma10`          DECIMAL(10,6)                          COMMENT '与 MA10 的乖离率',
  `dist_to_ma20`          DECIMAL(10,6)                          COMMENT '与 MA20 的乖离率',
  `dist_to_ma60`          DECIMAL(10,6)                          COMMENT '与 MA60 的乖离率',
  `dist_to_ma250`         DECIMAL(10,6)                          COMMENT '与 MA250 的乖离率',
  `ma_convergence`        DECIMAL(10,6)                          COMMENT '均线粘合度',
  -- 形态派生
  `box_test_count_60d`    TINYINT                                COMMENT '60 日内压力位测试次数',
  `box_resistance_level`  DECIMAL(16,4)                          COMMENT '识别出的压力位价格',
  `is_first_recovery_ma250` TINYINT(1)                           COMMENT '是否首次站稳 MA250',
  -- 扩展与元数据
  `extra_metrics`         JSON,
  `schema_version`        VARCHAR(10)  DEFAULT 'v1.0',
  `created_at`            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  `updated_at`            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`trade_date`, `ts_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;
```

### E1-S2 异动信号统一池表 (ads_l8_unified_signal)

三类异动池物理合表,增强标签体系与印证评估。

```sql
CREATE TABLE `ads_l8_unified_signal` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`           BIGINT UNSIGNED NOT NULL DEFAULT 1,
  `trade_date`        DATE            NOT NULL,
  `ts_code`           VARCHAR(20)     NOT NULL,
  `name`              VARCHAR(50)     NOT NULL,
  `industry_sw1`      VARCHAR(50),
  `industry_sw3`      VARCHAR(50),
  -- 类型
  `pool_type`         VARCHAR(16)     NOT NULL                  COMMENT 'strong/early/trap',
  `signal_type`       VARCHAR(40)     NOT NULL,
  `signal_subtype`    VARCHAR(40),
  -- 行情与特征
  `pct_chg`           DECIMAL(10,6),
  `turnover_rate`     DECIMAL(10,6),
  `volume_ratio_5d`   DECIMAL(10,6),
  `amount`            DECIMAL(20,2),
  `main_net_inflow`   DECIMAL(20,2),
  `signal_features`   JSON                                        COMMENT '差异化指标',
  `tags`              JSON                                        COMMENT '多维度标签',
  -- 印证评估
  `resonance_level`       TINYINT                                COMMENT '共振等级 1-5',
  `resonance_dimensions`  JSON                                    COMMENT '共振维度详情',
  `resonance_score`       DECIMAL(6,2),
  `counter_signals`       JSON                                    COMMENT '反向信号',
  `counter_signal_score`  DECIMAL(6,2),
  `temporal_resonance`    JSON                                    COMMENT '时间窗口共振',
  -- 评分
  `raw_score`         DECIMAL(6,2),
  `score_l3_capital`  DECIMAL(6,2),
  `score_l4_emotion`  DECIMAL(6,2),
  `score_user_pref`   DECIMAL(6,2),
  `score_dedup_pen`   DECIMAL(6,2),
  `composite_score`   DECIMAL(6,2)                                COMMENT '综合评分',
  -- 弹性设计
  `excluded_reasons`  JSON                                        COMMENT '排除理由',
  `default_visible`   TINYINT(1)      DEFAULT 1,
  `explanation_zh`    VARCHAR(500)                                COMMENT '中文解释',
  -- 扩展与元数据
  `extra`             JSON,
  `schema_version`    VARCHAR(10)     DEFAULT 'v1.0',
  `compute_version`   VARCHAR(20),
  `is_deleted`        TINYINT(1)      DEFAULT 0,
  `created_at`        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_signal` (`user_id`, `trade_date`, `ts_code`, `pool_type`, `signal_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;
```

### E1-S3 标签字典与关系表 (dim_tag_dictionary/relation)

```sql
CREATE TABLE `dim_tag_dictionary` (
  `tag_code`         VARCHAR(40)  NOT NULL PRIMARY KEY,
  `tag_name_cn`      VARCHAR(50)  NOT NULL,
  `tag_category`     VARCHAR(20)  NOT NULL,
  `tag_subcategory`  VARCHAR(20),
  `tag_description`  VARCHAR(200),
  `display_order`    INT          DEFAULT 100,
  `is_active`        TINYINT(1)   DEFAULT 1,
  `tag_meta`         JSON,
  `created_at`       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `dim_tag_relation` (
  `tag_a`            VARCHAR(40)  NOT NULL,
  `tag_b`            VARCHAR(40)  NOT NULL,
  `relation_type`    VARCHAR(20)  NOT NULL COMMENT 'mutex/imply/correlate',
  PRIMARY KEY (`tag_a`, `tag_b`, `relation_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### E1-S4 筛选模板表 (dim_filter_profile)

```sql
CREATE TABLE `dim_filter_profile` (
  `profile_code`     VARCHAR(40)  NOT NULL PRIMARY KEY,
  `profile_name`     VARCHAR(50)  NOT NULL,
  `rules_json`       JSON         NOT NULL,
  `is_system`        TINYINT(1)   DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### E1-S5 市场状态表 (ads_market_state_daily)

```sql
CREATE TABLE `ads_market_state_daily` (
  `trade_date`           DATE         NOT NULL PRIMARY KEY,
  `is_normal`            TINYINT(1)   DEFAULT 1,
  `abnormal_reasons`     JSON,
  `signal_reliability`   DECIMAL(4,2) DEFAULT 1.00 COMMENT '可信度系数 0-1',
  `created_at`           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### E1-S6 Top 10 推送清单表 (app_anomaly_top10_daily)

```sql
CREATE TABLE `app_anomaly_top10_daily` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `user_id`           BIGINT UNSIGNED NOT NULL DEFAULT 1,
  `trade_date`        DATE            NOT NULL,
  `rank_no`           TINYINT         NOT NULL,
  `signal_id`         BIGINT UNSIGNED NOT NULL,
  `ts_code`           VARCHAR(20)     NOT NULL,
  `name`              VARCHAR(50)     NOT NULL,
  `pool_type`         VARCHAR(16)     NOT NULL,
  `composite_score`   DECIMAL(6,2)    NOT NULL,
  `quota_slot`        VARCHAR(20)     NOT NULL COMMENT 'quota_strong/early/trap/filled/l5_must',
  `profile_code`      VARCHAR(40),
  `headline`          VARCHAR(200),
  `key_features`      JSON,
  UNIQUE KEY `uk_user_date_rank` (`user_id`, `trade_date`, `rank_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### E1-S7 评分权重配置表 (dim_anomaly_score_weight)

```sql
CREATE TABLE `dim_anomaly_score_weight` (
  `version`           VARCHAR(20)  NOT NULL,
  `weight_key`        VARCHAR(40)  NOT NULL,
  `weight_value`      DECIMAL(6,4) NOT NULL,
  `is_active`         TINYINT(1)   DEFAULT 0,
  PRIMARY KEY (`version`, `weight_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### E1-S8 用户板块偏好表 (dim_user_sector_pref)

```sql
CREATE TABLE `dim_user_sector_pref` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `user_id`           BIGINT UNSIGNED NOT NULL DEFAULT 1,
  `sector_type`       VARCHAR(16)     NOT NULL,
  `sector_code`       VARCHAR(50)     NOT NULL,
  `sector_name`       VARCHAR(50)     NOT NULL,
  `weight`            DECIMAL(4,2)    NOT NULL DEFAULT 1.00,
  `is_active`         TINYINT(1)      NOT NULL DEFAULT 1,
  UNIQUE KEY `uk_user_sector` (`user_id`, `sector_type`, `sector_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```
