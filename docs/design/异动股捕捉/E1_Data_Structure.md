# E1 · 数据结构

### E1-S1 异动信号统一池表

> **作为** 复盘者,**我希望** 三类异动池(强/启动前/陷阱)在同一张表中按 `pool_type` 区分,**以便** 综合评分函数和 Top 10 排序能在单表内完成,避免多表 JOIN。

#### E1-S1-T1 DDL

```sql
-- 在项目数据库执行
CREATE TABLE `ads_l8_unified_signal` (
  `trade_date`        DATE         NOT NULL                  COMMENT '交易日',
  `ts_code`           VARCHAR(20)  NOT NULL                  COMMENT '股票代码,如 688256.SH',
  `name`              VARCHAR(50)  NOT NULL                  COMMENT '股票名称',
  `industry_sw1`      VARCHAR(50)                            COMMENT '申万一级行业',
  `industry_sw3`      VARCHAR(50)                            COMMENT '申万三级行业',

  `pool_type`         VARCHAR(16)  NOT NULL                  COMMENT 'strong/early/trap',
  `signal_type`       VARCHAR(40)  NOT NULL                  COMMENT '具体信号类型,见附录 A',
  `signal_subtype`    VARCHAR(40)                            COMMENT '组合信号的子类标识',

  -- 基础行情(便于排序与展示)
  `pct_chg`           DECIMAL(10,6)                          COMMENT '当日涨跌幅,小数',
  `turnover_rate`     DECIMAL(10,6)                          COMMENT '当日换手率,小数',
  `volume_ratio_5d`   DECIMAL(10,6)                          COMMENT '量比 5 日均值,核心字段',
  `amount`            DECIMAL(20,2)                          COMMENT '当日成交额,元',
  `main_net_inflow`   DECIMAL(20,2)                          COMMENT '主力净流入,元',

  -- 信号特征(各池差异化指标存 JSON)
  `signal_features`   JSON                                   COMMENT '池差异化指标,见附录 A',

  -- 评分
  `raw_score`         DECIMAL(6,2)                           COMMENT '原始信号强度,0-100',
  `score_l3_capital`  DECIMAL(6,2)                           COMMENT 'L3 资金维度子分,0-100',
  `score_l4_emotion`  DECIMAL(6,2)                           COMMENT 'L4 情绪维度子分,0-100',
  `score_user_pref`   DECIMAL(6,2)                           COMMENT '个人板块偏好加分,0-100',
  `score_dedup_pen`   DECIMAL(6,2)                           COMMENT '重复跟踪压制扣分,0-100',
  `composite_score`   DECIMAL(6,2)                           COMMENT '综合评分,排序用',

  -- 元数据
  `compute_version`   VARCHAR(20)                            COMMENT '评分版本号,便于权重调整后追溯',
  `created_at`        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (`trade_date`, `ts_code`, `pool_type`, `signal_type`),
  KEY `idx_date_pool_score`   (`trade_date`, `pool_type`, `composite_score`),
  KEY `idx_date_score`        (`trade_date`, `composite_score`),
  KEY `idx_code_date`         (`ts_code`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC
  COMMENT='ADS-L8 异动统一池(strong/early/trap)';
```

**Trade-off**:主键包含 `signal_type` 是因为同一只股票可能同时命中多个信号(如既是涨停又是龙头预备役),允许多行存在,Top 10 生成时会去重取最高分。

#### E1-S1-T2 `signal_features` JSON 字段约定

不同 `pool_type` 下 JSON 结构不同,但顶层键统一可枚举,便于解析。详见 [附录 A](#附录-a-信号类型字典)。

#### E1-S1-T2-AC 验收标准

> **Given** L8 ETL 已完成,L8.5/L8.6 信号已计算  
> **When** 当日 18:00 查询 `SELECT pool_type, COUNT(*) FROM ads_l8_unified_signal WHERE trade_date = @td GROUP BY pool_type`  
> **Then** 返回 3 行(strong/early/trap),且 strong 池数量 ≥ 30 行(L8 同步保底)

> **Given** 任意一行异动信号  
> **When** 查询 `composite_score`  
> **Then** 值非空且 ∈ [0, 100]

---

### E1-S2 Top 10 推送清单表

> **作为** 用户,**我希望** 每天有一份固定 10 条的推送清单按机会/潜力/风险分类,**以便** 高效完成训练样本的选择。

#### E1-S2-T1 DDL

```sql
CREATE TABLE `app_anomaly_top10_daily` (
  `trade_date`        DATE         NOT NULL,
  `rank_no`           TINYINT      NOT NULL                  COMMENT '1-10',
  `ts_code`           VARCHAR(20)  NOT NULL,
  `name`              VARCHAR(50)  NOT NULL,
  `industry_sw1`      VARCHAR(50),
  `pool_type`         VARCHAR(16)  NOT NULL                  COMMENT 'strong/early/trap',
  `signal_type`       VARCHAR(40)  NOT NULL,
  `signal_subtype`    VARCHAR(40),
  `composite_score`   DECIMAL(6,2) NOT NULL,
  `quota_slot`        VARCHAR(16)  NOT NULL                  COMMENT 'quota_strong/quota_early/quota_trap/quota_filled',
  `headline`          VARCHAR(200)                           COMMENT '一句话信号说明,前端直接展示',
  `key_features`      JSON                                   COMMENT '前端展示的 3-5 个关键指标',
  `created_at`        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (`trade_date`, `rank_no`),
  KEY `idx_date_pool` (`trade_date`, `pool_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC
  COMMENT='APP-每日 Top 10 推送清单';
```

`quota_slot` 区分该条目是占用了"自身池配额"还是"动态填补名额",便于事后统计配额使用情况。

#### E1-S2-T1-AC 验收标准

> **Given** 当日已生成完整 Top 10  
> **When** 查询 `SELECT rank_no, pool_type, quota_slot FROM app_anomaly_top10_daily WHERE trade_date = @td ORDER BY rank_no`  
> **Then** 返回 ≤ 10 行,`rank_no` 连续递增,`quota_slot` 值在 4 个枚举内

---

### E1-S3 评分权重配置表(支持热调参)

> **作为** 系统维护者,**我希望** 评分权重存在数据库,**以便** 后续根据命中率反推调整权重,无需改代码。

#### E1-S3-T1 DDL

```sql
CREATE TABLE `dim_anomaly_score_weight` (
  `version`           VARCHAR(20)  NOT NULL                  COMMENT '版本号,如 v20260502',
  `weight_key`        VARCHAR(40)  NOT NULL                  COMMENT '权重项标识',
  `weight_value`      DECIMAL(6,4) NOT NULL                  COMMENT '权重值',
  `weight_desc`       VARCHAR(200)                           COMMENT '说明',
  `is_active`         TINYINT(1)   NOT NULL DEFAULT 0        COMMENT '当前激活版本',
  `effective_from`    DATE                                   COMMENT '生效日期',
  `created_at`        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (`version`, `weight_key`),
  KEY `idx_active` (`is_active`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC
  COMMENT='异动评分权重配置';
```

#### E1-S3-T2 初始权重数据

```sql
INSERT INTO `dim_anomaly_score_weight`
    (version, weight_key, weight_value, weight_desc, is_active, effective_from) VALUES
-- 评分权重
('v20260502', 'alpha_raw_score',     0.4000, '原始信号强度权重',                 1, '2026-05-02'),
('v20260502', 'beta_l3_capital',     0.2500, 'L3 资金评分权重',                  1, '2026-05-02'),
('v20260502', 'gamma_l4_emotion',    0.1500, 'L4 情绪评分权重',                  1, '2026-05-02'),
('v20260502', 'epsilon_user_pref',   0.1000, '个人板块偏好权重',                 1, '2026-05-02'),
('v20260502', 'zeta_dedup_penalty',  0.1000, '7 日重复跟踪压制权重(扣分)',     1, '2026-05-02'),
-- Top 10 配额
('v20260502', 'pool_strong_quota',   4.0000, 'Top10 中强异动配额',               1, '2026-05-02'),
('v20260502', 'pool_early_quota',    4.0000, 'Top10 中启动前配额',               1, '2026-05-02'),
('v20260502', 'pool_trap_quota',     2.0000, 'Top10 中陷阱配额',                 1, '2026-05-02'),
('v20260502', 'pool_trap_min',       1.0000, '陷阱保留最小名额',                 1, '2026-05-02'),
-- 通用参数
('v20260502', 'dedup_window_days',   7.0000, '重复跟踪压制窗口(日)',           1, '2026-05-02'),
('v20260502', 'dedup_score_threshold', 60.00, '判定为"被跟踪"的最低分数',        1, '2026-05-02');
```

**Trade-off**:把权重和配额放进同一张表(用 `weight_key` 区分语义),好处是统一接口、统一版本管理;坏处是字段含义稍弱化(配额其实不是"权重")。可接受,优于多张配置表的复杂度。

---

### E1-S4 用户板块偏好表

> **作为** 用户,**我希望** 标记自己关注的板块,**以便** 这些板块的异动信号在推送中被优先排序。

#### E1-S4-T1 DDL

```sql
CREATE TABLE `dim_user_sector_pref` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`           BIGINT UNSIGNED NOT NULL DEFAULT 1     COMMENT '当前单用户系统默认 1',
  `sector_type`       VARCHAR(16)     NOT NULL               COMMENT 'industry_sw1/concept',
  `sector_code`       VARCHAR(50)     NOT NULL,
  `sector_name`       VARCHAR(50)     NOT NULL,
  `weight`            DECIMAL(4,2)    NOT NULL DEFAULT 1.00  COMMENT '加权倍数,1.0-3.0',
  `is_active`         TINYINT(1)      NOT NULL DEFAULT 1,
  `created_at`        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_sector` (`user_id`, `sector_type`, `sector_code`),
  KEY `idx_user_active` (`user_id`, `is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC
  COMMENT='用户板块偏好';
```

#### E1-S4-T2 示例配置

```sql
-- 示例:用户标记 AI / 半导体 / 军工 为关注板块
INSERT INTO `dim_user_sector_pref`
    (user_id, sector_type, sector_code, sector_name, weight) VALUES
(1, 'industry_sw1', '801080', '计算机',       1.5),
(1, 'industry_sw1', '801221', '半导体',       1.5),
(1, 'industry_sw1', '801740', '国防军工',     1.2);
```
