-- 异动捕捉模块 v1.1 数据库初始化
-- 日期: 2026-05-02

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 1. 派生指标层 (ads_stock_derived_metrics)
-- ----------------------------
CREATE TABLE IF NOT EXISTS `ads_stock_derived_metrics` (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='ADS-派生指标层';

-- ----------------------------
-- 2. 异动信号统一池表 (ads_l8_unified_signal)
-- ----------------------------
CREATE TABLE IF NOT EXISTS `ads_l8_unified_signal` (
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
  UNIQUE KEY `uk_signal` (`user_id`, `trade_date`, `ts_code`, `pool_type`, `signal_type`),
  KEY `idx_date_pool_score` (`trade_date`, `pool_type`, `composite_score`),
  KEY `idx_code_date` (`ts_code`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='ADS-异动信号统一池';

-- ----------------------------
-- 3. 标签字典与关系表
-- ----------------------------
CREATE TABLE IF NOT EXISTS `dim_tag_dictionary` (
  `tag_code`         VARCHAR(40)  NOT NULL PRIMARY KEY,
  `tag_name_cn`      VARCHAR(50)  NOT NULL,
  `tag_category`     VARCHAR(20)  NOT NULL,
  `tag_subcategory`  VARCHAR(20),
  `tag_description`  VARCHAR(200),
  `display_order`    INT          DEFAULT 100,
  `is_active`        TINYINT(1)   DEFAULT 1,
  `tag_meta`         JSON,
  `created_at`       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='DIM-标签字典';

CREATE TABLE IF NOT EXISTS `dim_tag_relation` (
  `tag_a`            VARCHAR(40)  NOT NULL,
  `tag_b`            VARCHAR(40)  NOT NULL,
  `relation_type`    VARCHAR(20)  NOT NULL COMMENT 'mutex/imply/correlate',
  PRIMARY KEY (`tag_a`, `tag_b`, `relation_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='DIM-标签关系';

-- ----------------------------
-- 4. 筛选模板表
-- ----------------------------
CREATE TABLE IF NOT EXISTS `dim_filter_profile` (
  `profile_code`     VARCHAR(40)  NOT NULL PRIMARY KEY,
  `profile_name`     VARCHAR(50)  NOT NULL,
  `description`      VARCHAR(200),
  `rules_json`       JSON         NOT NULL,
  `is_system`        TINYINT(1)   DEFAULT 1,
  `display_order`    INT          DEFAULT 100,
  `created_at`       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='DIM-筛选模板';

CREATE TABLE IF NOT EXISTS `dim_user_active_profile` (
  `user_id`          BIGINT UNSIGNED NOT NULL DEFAULT 1,
  `profile_code`     VARCHAR(40)     NOT NULL,
  `is_active`        TINYINT(1)      DEFAULT 1,
  `activated_at`     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='DIM-用户当前激活模板';

-- ----------------------------
-- 5. 市场状态表
-- ----------------------------
CREATE TABLE IF NOT EXISTS `ads_market_state_daily` (
  `trade_date`           DATE         NOT NULL PRIMARY KEY,
  `is_normal`            TINYINT(1)   DEFAULT 1,
  `csi300_pct_chg`       DECIMAL(10,6),
  `abnormal_reasons`     JSON,
  `signal_reliability`   DECIMAL(4,2) DEFAULT 1.00 COMMENT '可信度系数 0-1',
  `manual_override`      TINYINT(1)   DEFAULT 0,
  `note`                 VARCHAR(200),
  `extra`                JSON,
  `schema_version`       VARCHAR(10)  DEFAULT 'v1.0',
  `created_at`           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  `updated_at`           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ADS-市场状态';

-- ----------------------------
-- 6. Top 10 推送清单表
-- ----------------------------
CREATE TABLE IF NOT EXISTS `app_anomaly_top10_daily` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `user_id`           BIGINT UNSIGNED NOT NULL DEFAULT 1,
  `trade_date`        DATE            NOT NULL,
  `rank_no`           TINYINT         NOT NULL,
  `signal_id`         BIGINT UNSIGNED NOT NULL,
  `ts_code`           VARCHAR(20)     NOT NULL,
  `name`              VARCHAR(50)     NOT NULL,
  `industry_sw1`      VARCHAR(50),
  `pool_type`         VARCHAR(16)     NOT NULL,
  `signal_type`       VARCHAR(40)     NOT NULL,
  `signal_subtype`    VARCHAR(40),
  `composite_score`   DECIMAL(6,2)    NOT NULL,
  `resonance_level`   TINYINT,
  `quota_slot`        VARCHAR(20)     NOT NULL COMMENT 'quota_strong/early/trap/filled/l5_must',
  `profile_code`      VARCHAR(40),
  `headline`          VARCHAR(200),
  `key_features`      JSON,
  `extra`             JSON,
  `schema_version`    VARCHAR(10)     DEFAULT 'v1.0',
  `created_at`        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_user_date_rank` (`user_id`, `trade_date`, `rank_no`),
  KEY `idx_date_pool` (`trade_date`, `pool_type`),
  KEY `idx_signal` (`signal_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='APP-每日 Top 10 推送清单';

-- ----------------------------
-- 7. 评分权重配置表
-- ----------------------------
CREATE TABLE IF NOT EXISTS `dim_anomaly_score_weight` (
  `version`           VARCHAR(20)  NOT NULL,
  `weight_key`        VARCHAR(40)  NOT NULL,
  `weight_value`      DECIMAL(6,4) NOT NULL,
  `weight_desc`       VARCHAR(200),
  `is_active`         TINYINT(1)   DEFAULT 0,
  `effective_from`    DATE,
  `created_at`        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`version`, `weight_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='DIM-评分权重配置';

-- ----------------------------
-- 8. 用户板块偏好表
-- ----------------------------
CREATE TABLE IF NOT EXISTS `dim_user_sector_pref` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `user_id`           BIGINT UNSIGNED NOT NULL DEFAULT 1,
  `sector_type`       VARCHAR(16)     NOT NULL COMMENT 'industry_sw1/concept',
  `sector_code`       VARCHAR(50)     NOT NULL,
  `sector_name`       VARCHAR(50)     NOT NULL,
  `weight`            DECIMAL(4,2)    NOT NULL DEFAULT 1.00,
  `is_active`         TINYINT(1)      NOT NULL DEFAULT 1,
  `extra`             JSON,
  `schema_version`    VARCHAR(10)     DEFAULT 'v1.0',
  `created_at`        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_user_sector` (`user_id`, `sector_type`, `sector_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='DIM-用户板块偏好';

-- ----------------------------
-- 9. 信号生命周期表 (Appendix C)
-- ----------------------------
CREATE TABLE IF NOT EXISTS `log_signal_lifecycle` (
  `id`               BIGINT UNSIGNED  AUTO_INCREMENT PRIMARY KEY,
  `original_id`      BIGINT UNSIGNED  NOT NULL COMMENT '关联统一信号表 id',
  `tracked_date`     DATE             NOT NULL,
  `state`            VARCHAR(20)      NOT NULL COMMENT 'active/continuing/reversed/failed',
  `state_features`   JSON,
  `delta_metrics`    JSON             COMMENT '相对触发日的变化指标',
  `extra`            JSON,
  `schema_version`   VARCHAR(10)      DEFAULT 'v1.0',
  `created_at`       TIMESTAMP        DEFAULT CURRENT_TIMESTAMP,
  KEY `idx_original` (`original_id`, `tracked_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='LOG-信号生命周期';


-- ----------------------------
-- 初始化基础数据
-- ----------------------------

-- 1. 评分权重 (v20260502)
INSERT IGNORE INTO `dim_anomaly_score_weight` (version, weight_key, weight_value, weight_desc, is_active, effective_from) VALUES
('v20260502', 'alpha_raw_score',     0.4000, '原始信号强度权重',                 1, '2026-05-02'),
('v20260502', 'beta_l3_capital',     0.2500, 'L3 资金评分权重',                  1, '2026-05-02'),
('v20260502', 'gamma_l4_emotion',    0.1500, 'L4 情绪评分权重',                  1, '2026-05-02'),
('v20260502', 'epsilon_user_pref',   0.1000, '个人板块偏好权重',                 1, '2026-05-02'),
('v20260502', 'zeta_dedup_penalty',  0.1000, '7 日重复跟踪压制权重(扣分)',     1, '2026-05-02'),
('v20260502', 'mu_resonance_boost',  0.1500, '共振等级加分系数(每升1级+15)',   1, '2026-05-02'),
('v20260502', 'nu_counter_penalty',  0.2000, '反向信号扣分系数',                 1, '2026-05-02'),
('v20260502', 'pool_strong_quota',   4.0000, 'Top10 中强异动配额',               1, '2026-05-02'),
('v20260502', 'pool_early_quota',    4.0000, 'Top10 中启动前配额',               1, '2026-05-02'),
('v20260502', 'pool_trap_quota',     2.0000, 'Top10 中陷阱配额',                 1, '2026-05-02'),
('v20260502', 'pool_trap_min',       1.0000, '陷阱保留最小名额',                 1, '2026-05-02'),
('v20260502', 'l5_must_max',         3.0000, 'L5 共振必入最多条数',              1, '2026-05-02'),
('v20260502', 'dedup_window_days',   7.0000, '重复跟踪压制窗口(日)',           1, '2026-05-02'),
('v20260502', 'dedup_score_threshold', 60.00, '判定为"被跟踪"的最低分数',        1, '2026-05-02');

-- 2. 标签关系
INSERT IGNORE INTO `dim_tag_relation` (tag_a, tag_b, relation_type) VALUES
('pre_zt_low_volume',  'pre_zt_high_volume',     'mutex'),
('pre_zt_consolidation','pre_zt_already_pulled', 'mutex'),
('pre_zt_consolidation','pre_zt_pullback',       'mutex'),
('zt_one_word',        'zt_late_attack',         'mutex'),
('zt_open_to_close',   'zt_late_attack',         'mutex'),
('zt_one_word',        'zt_open_to_close',       'imply'),
('first_board',        'zt',                     'imply'),
('sector_leader',      'first_board',            'correlate'),
('main_inflow_strong', 'lhb_inst_buy',           'correlate');

-- 3. 预设 Profile
INSERT IGNORE INTO `dim_filter_profile` (profile_code, profile_name, description, rules_json, is_system, display_order) VALUES
('profile_default', '新手默认', '标准过滤,适合还没形成偏好的阶段', '{"exclude_tags": ["st", "new_stock", "delist"], "exclude_combos": [["zt_one_word", "low_amount"], ["micro_cap", "low_price", "sector_follower"]], "prefer_tags": [], "pool_quotas": {"strong": 4, "early": 4, "trap": 2}, "top_n": 10, "min_resonance": 1, "trap_min": 1}', 1, 100),
('profile_short_term', '短线接力派', '重点关注连板梯队 + 板块龙头', '{"exclude_tags": ["st", "new_stock", "delist", "pre_zt_dead_cat_bounce", "earnings_beat"], "prefer_tags": ["sector_leader", "3_board", "n_board", "first_board", "mainline_resonance"], "boost_factor": 1.5, "pool_quotas": {"strong": 6, "early": 3, "trap": 1}, "top_n": 10, "min_resonance": 2, "trap_min": 1}', 1, 200),
('profile_value_observer', '中线机构派', '重点关注机构入场 + 业绩驱动', '{"exclude_tags": ["st", "new_stock", "micro_cap", "low_price", "zt_one_word", "pre_zt_already_pulled"], "prefer_tags": ["lhb_inst_buy", "earnings_beat", "breakout_250d", "main_inflow_strong"], "boost_factor": 1.6, "pool_quotas": {"strong": 3, "early": 5, "trap": 2}, "top_n": 10, "min_resonance": 2, "trap_min": 1}', 1, 300),
('profile_sector_research', '板块研究派', '看板块共振,不看个股博弈', '{"exclude_tags": ["st", "new_stock", "sector_isolated"], "prefer_tags": ["sector_leader", "mainline_resonance", "concept_hot"], "boost_factor": 2.0, "pool_quotas": {"strong": 5, "early": 4, "trap": 1}, "top_n": 10, "min_resonance": 3, "trap_min": 0}', 1, 400),
('profile_research_mode', '全量研究模式', '什么都看,做对照研究', '{"exclude_tags": [], "exclude_combos": [], "prefer_tags": [], "pool_quotas": {"strong": 20, "early": 20, "trap": 10}, "top_n": 50, "min_resonance": 1, "trap_min": 0, "show_excluded": true}', 1, 999);

-- 4. 激活默认 Profile
INSERT IGNORE INTO `dim_user_active_profile` (user_id, profile_code, is_active)
VALUES (1, 'profile_default', 1);

-- 5. 标签字典 (Appendix A)
INSERT IGNORE INTO `dim_tag_dictionary` (tag_code, tag_name_cn, tag_category, display_order) VALUES
('zt', '涨停', 'price', 10),
('dt', '跌停', 'price', 20),
('first_board', '首板', 'price', 30),
('2_board', '二板', 'price', 31),
('3_board', '三板', 'price', 32),
('n_board', 'N 连板(≥4)', 'price', 33),
('breakout_60d', '突破 60 日新高', 'price', 40),
('breakout_250d', '突破年线高点', 'price', 41),
('main_inflow_strong', '主力大幅净流入', 'capital', 10),
('main_outflow', '主力净流出', 'capital', 11),
('lhb_listed', '上龙虎榜', 'capital', 20),
('lhb_inst_buy', '龙虎榜机构净买', 'capital', 21),
('lhb_yz_buy', '龙虎榜游资净买', 'capital', 22),
('capital_rank_jump', '资金排名跃升', 'capital', 30),
('margin_buy_strong', '融资买入占比高', 'capital', 40),
('sector_leader', '板块龙头', 'sector', 10),
('sector_follower', '板块跟随者', 'sector', 11),
('sector_isolated', '板块孤立', 'sector', 12),
('mainline_resonance', '主线共振', 'sector', 20),
('concept_hot', '概念热点', 'sector', 21),
('announcement_today', '当日有公告', 'catalyst', 10),
('no_announcement', '无公告催化', 'catalyst', 11),
('earnings_beat', '业绩超预期', 'catalyst', 20),
('earnings_disappoint', '业绩不及预期', 'catalyst', 21),
('policy_today', '政策催化', 'catalyst', 30),
('holder_reduce', '大股东减持', 'catalyst', 40),
('high_position', '高位', 'history', 10),
('low_position', '低位', 'history', 11),
('continuation_5d', '5 日延续', 'history', 20),
('continuation_20d', '20 日延续', 'history', 21),
('rank_up_60d', '60 日排名上升', 'history', 22),
('pre_zt_low_volume', '涨停前缩量蓄势', 'pattern', 10),
('pre_zt_high_volume', '涨停前放量启动', 'pattern', 11),
('pre_zt_consolidation', '涨停前横盘整理', 'pattern', 12),
('pre_zt_pullback', '涨停前回调反弹', 'pattern', 13),
('pre_zt_already_pulled', '涨停前已加速', 'pattern', 14),
('pre_zt_dead_cat_bounce', '死猫跳涨停', 'pattern', 15),
('pre_zt_first_recovery', '首次站稳年线涨停', 'pattern', 16),
('zt_one_word', '一字板', 'pattern', 20),
('zt_t_shape', 'T 字板', 'pattern', 21),
('zt_open_to_close', '早盘强封', 'pattern', 22),
('zt_late_attack', '尾盘攻击', 'pattern', 23),
('pre_dt_high_position', '高位跌停', 'pattern', 30),
('pre_dt_continuous_decline', '加速下跌跌停', 'pattern', 31),
('dt_one_word', '一字跌停', 'pattern', 32),
('breakout_box_60d', '60 日箱体突破', 'pattern', 40),
('breakout_consolidation', '整理后突破', 'pattern', 41),
('pullback_to_ma10', '回踩 10 日线反弹', 'pattern', 42),
('st', 'ST 股', 'anomaly', 10),
('new_stock', '新股次新', 'anomaly', 20),
('delist', '退市整理', 'anomaly', 30),
('micro_cap', '微盘股', 'anomaly', 40),
('low_price', '低价股', 'anomaly', 50),
('zombie_stock', '僵尸股', 'anomaly', 60),
('sox_up_overnight', '费城半导体上涨', 'external', 10),
('us_tech_strong', '美股科技强势', 'external', 11),
('hk_tech_strong', '港股科技强势', 'external', 12),
('external_weak', '外部市场偏弱', 'external', 13);

SET FOREIGN_KEY_CHECKS = 1;
