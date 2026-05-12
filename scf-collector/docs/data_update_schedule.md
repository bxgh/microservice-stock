# 数据原始采集计划手册 v0.2 漏项补遗

> **本文件用途**：作为 v0.2 文档的**补丁包**，专项处理评审中发现的 11 张漏掉的原始数据表，以及 1 处关键备注错误。
> **关联文档**：`data_update_schedule_v0.2.md`。本文件预期下一版（v0.3）合并入主文档。
> **生成日期**：2026-05-12

---

## 背景

v0.2 文档发布后 review 发现以下结构性问题：

1. **复权因子完全未规划**：`stock_kline_daily` 实测落库为**不复权原始价**（用户已确认），v0.2 备注「前复权数据」为错误描述，且**全文档无 `ods_adj_factor` 采集任务**
2. **资金五维理解偏差**：`PROJECT_OVERVIEW` 第 4 章明确为「主力 / 北向 / 两融 / ETF / 龙虎榜」5 维，v0.2 漏了**主力维**（`pro.moneyflow`），多算了「大宗 / 游资」当独立维
3. **L2 行业成员关系无显式维表**：当前 `ads_l2_industry_daily` 已跑通 31 行业，但 TABLES_INDEX 无 `dim_sw_industry_member`，属 **schema 漂移**（实施侧大概率运行时调用 `pro.index_member()` 或误用中信分类）
4. **ETF 申赎计算依赖 `nav` 但无 nav 采集任务**：v0.2 第 5.5 节公式 `share_chg × nav × 1e8` 中的 `nav` 数据源缺失

补遗合计 **11 张新表 + 1 处备注修正**。

---

## 目标

- 补齐 v0.2 漏掉的 11 张原始数据表清单
- 修正 `stock_kline_daily` 备注错误
- 评估对**已产出 ads_\* 数据**的污染范围（是否需要历史回灌）
- 提供 P0 表的 schema 草案，供 Gemini 立即落地

---

## 范围

| 包含 | 不包含 |
|---|---|
| 11 张漏掉的 ods_* / dim_* 表的采集任务定义 | ETL 计算层重构 |
| 关键 P0 表的 schema 草案 | 跨网同步链路（仍走 v1.1 E4） |
| 已产出 ads_* 数据的污染评估 | 实际重灌脚本 |
| 备注错误修正 | 完整 v0.3 文档重写（合入主文档后单独发） |

## 非目标

- 不重写 v0.2 全文，仅以补遗形式存在
- 不规划 ads_* 层重构（先把原始数据修好再说）
- 不定义 `ods_adj_factor` 应用到下游的具体 ETL 逻辑

---

## E1 复权因子缺失（P0 紧急）

**Epic 描述**：补齐复权因子采集 + 评估对已产出技术指标的污染范围。预计耗时 1 工作日采集 + 3-5 工作日历史回灌。

### E1-S1 建立 `ods_adj_factor` 采集任务

**作为** L2 / L5 / L8 计算层，**我希望** 拿到每只票每个交易日的复权因子，**以便** 正确计算复权后的 K 线衍生指标（均线 / 涨跌幅 / 波动率 / dist_to_ma 等）。

#### 任务

- E1-S1-T1 在采集层新增 `ods_adj_factor` 表
- E1-S1-T2 在调度配置中新增采集任务，时机 16:30（与 `stock_kline_daily` 同批）
- E1-S1-T3 历史回补：拉取 2010-01-01 起全 A 复权因子
- E1-S1-T4 采集结束写 `data_readiness`

#### 表结构草案

```sql
CREATE TABLE `ods_adj_factor` (
  `ts_code`     VARCHAR(20) NOT NULL,
  `trade_date`  DATE        NOT NULL,
  `adj_factor`  DECIMAL(20,6) NOT NULL COMMENT '复权因子,基期=1.0',
  `created_at`  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`  TINYINT(1)  DEFAULT 0,
  PRIMARY KEY (`ts_code`, `trade_date`),
  KEY `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC COMMENT='Tushare 复权因子,每日全 A';
```

#### 上游接口

```python
# Tushare 调用示例
ts.pro_api().adj_factor(ts_code='', trade_date='20260512')
# 全 A 单日返回约 5000 行
```

#### 验收标准（AC）

- **AC1**：日度采集就绪
  - **Given** 交易日 16:30 触发采集
  - **When** Tushare 接口返回数据
  - **Then** `ods_adj_factor` 当日新增 ≈ 5000 行（与 `stock_kline_daily` 行数差异 < 1%），且 `data_readiness` 写入 `('adj_factor', :trade_date, 'ready', 5000±)`

- **AC2**：历史回补完整
  - **Given** 历史回补脚本对 2010-01-01 至今全 A 执行
  - **When** 回补完成
  - **Then** 任取一只 2023-06-30 除权的票（如 `600519.SH`），`adj_factor` 在除权日**有跳变**，且与 Tushare API 实时拉取的结果一致

- **AC3**：单位与基准正确
  - **Given** 任一票最早的 `trade_date`
  - **When** 查询其 `adj_factor`
  - **Then** 值为 `1.000000`（基期约定）；后续日期 ≥ 该值（前复权基准）

### E1-S2 修正 v0.2 备注 + 评估 ads_* 污染

**作为** 数据治理者，**我希望** 知道当前 ads_* 层用了不复权价的范围，**以便** 评估历史数据是否需要回灌。

#### 任务

- E1-S2-T1 修正 v0.2 文档第 2 节 `stock_kline_daily` 的「前复权数据」备注，改为「不复权原始价；前复权需 JOIN `ods_adj_factor`」
- E1-S2-T2 自检 SQL，确认 `ads_stock_derived_metrics` 当前实现是否做了复权
- E1-S2-T3 如未做复权，列出受影响的 ads_* / app_* 表清单
- E1-S2-T4 制定回灌优先级（建议：近 1 年 P0，1-3 年 P1，> 3 年 P2）

#### 自检 SQL

```sql
-- 核查 1: stock_kline_daily 除权日跳变(确认不复权)
SELECT trade_date, close, pre_close,
       ROUND((close - pre_close) / pre_close * 100, 2) AS jump_pct
FROM stock_kline_daily
WHERE ts_code = '600519.SH'
  AND trade_date BETWEEN '2023-06-28' AND '2023-07-04'
ORDER BY trade_date;
-- 预期: 2023-06-30 jump_pct < -15% (除权日)

-- 核查 2: ads_stock_derived_metrics 的 dist_to_ma20 是否在除权日突变
SELECT ts_code, trade_date, dist_to_ma20
FROM ads_stock_derived_metrics
WHERE ts_code = '600519.SH'
  AND trade_date BETWEEN '2023-06-28' AND '2023-07-10'
ORDER BY trade_date;
-- 若 06-30 的 dist_to_ma20 突变 > 5%, 则 100% 未做复权,所有派生指标受污染
```

#### 验收标准（AC）

- **AC1**：自检结论明确
  - **Given** 上述两条 SQL 在生产库执行
  - **When** 拿到结果
  - **Then** 形成结论文档「`ads_stock_derived_metrics` 是否做了复权处理 = 是/否」

- **AC2**：受污染表清单完整
  - **Given** 自检结论为「未做复权」
  - **When** 输出受影响表清单
  - **Then** 至少覆盖：`ads_stock_derived_metrics` / `ads_l8_unified_signal` / `ads_l2_industry_daily`（行业指数自身包含成分股复权）/ 第 5 章异动评分 / 第 8 章 outcome_inference 验证数据

---

## E2 行业 / 概念成员关系缺失（P0）

**Epic 描述**：补齐申万行业 + 同花顺概念的成员归属维表，消除当前 schema 漂移。预计耗时 2 工作日。

### E2-S1 建立 `dim_sw_industry_member`

**作为** L2 行业广度计算（`internal_breadth = 行业内上涨股数 / 总成员数`），**我希望** 有一张拉链表记录每只票的申万 L1 / L2 归属及历史变更，**以便** 行业广度计算口径正确、可历史回算。

#### 任务

- E2-S1-T1 建表 `dim_sw_industry_member`
- E2-S1-T2 全量初始化：从 Tushare `pro.index_member_all()` 拉一次
- E2-S1-T3 月更增量：每月 1 号 06:30 触发，对比变化以拉链方式更新
- E2-S1-T4 提供 `is_in_industry(ts_code, sw_l1_code, trade_date)` 这类查询的视图或 SQL 范式（供下游 ETL 复用）

#### 表结构草案

```sql
CREATE TABLE `dim_sw_industry_member` (
  `id`          BIGINT      NOT NULL AUTO_INCREMENT,
  `ts_code`     VARCHAR(20) NOT NULL,
  `sw_l1_code`  VARCHAR(10) NOT NULL COMMENT '申万一级行业代码,如 801010.SI',
  `sw_l1_name`  VARCHAR(50) NOT NULL,
  `sw_l2_code`  VARCHAR(10) DEFAULT NULL,
  `sw_l2_name`  VARCHAR(50) DEFAULT NULL,
  `in_date`     DATE        NOT NULL COMMENT '纳入日',
  `out_date`    DATE        DEFAULT NULL COMMENT '剔除日,NULL=仍在',
  `is_active`   TINYINT(1)  DEFAULT 1,
  `created_at`  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`  TINYINT(1)  DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ts_l1_in` (`ts_code`, `sw_l1_code`, `in_date`),
  KEY `idx_ts_code` (`ts_code`),
  KEY `idx_sw_l1_active` (`sw_l1_code`, `is_active`),
  KEY `idx_in_out_date` (`in_date`, `out_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC COMMENT='申万行业成员拉链表';
```

#### 验收标准（AC）

- **AC1**：成员关系覆盖完整
  - **Given** 全量初始化完成
  - **When** 查询 `SELECT COUNT(DISTINCT ts_code) FROM dim_sw_industry_member WHERE is_active=1`
  - **Then** 结果 ≈ 全 A 上市股票数（5000+），不能有大批量未归类

- **AC2**：历史变更可追溯
  - **Given** 某只票历史上发生过行业调整（如「东方财富」从「计算机」调入「非银金融」）
  - **When** 用 `in_date` / `out_date` 过滤查询
  - **Then** 能拿到该票在任意历史日期的正确行业归属，**不能用今天的口径回算历史**

- **AC3**：月更增量正确
  - **Given** 行业调整发生（旧归属 out_date 不为 NULL，新归属 in_date 为调整日）
  - **When** 月更任务执行
  - **Then** 拉链表记录完整变更链，原行 `is_active=0`，新行 `is_active=1`

### E2-S2 建立 `dim_concept_member`

**作为** L2 概念板块计算，**我希望** 知道每只票属于哪些概念，**以便** 计算概念广度。

#### 任务

- E2-S2-T1 建表 `dim_concept_member`（结构类似 sw_member，但 ts_code 可属多个概念）
- E2-S2-T2 周更增量：每周一 06:30
- E2-S2-T3 同名概念去重处理（「机器人 / 机器人概念 / 人形机器人」三选一保留，规则 TBD）

#### 表结构草案

```sql
CREATE TABLE `dim_concept_member` (
  `id`            BIGINT      NOT NULL AUTO_INCREMENT,
  `ts_code`       VARCHAR(20) NOT NULL,
  `concept_code`  VARCHAR(20) NOT NULL,
  `concept_name`  VARCHAR(100) NOT NULL,
  `source`        VARCHAR(20) DEFAULT NULL COMMENT 'ths / akshare',
  `in_date`       DATE        NOT NULL,
  `out_date`      DATE        DEFAULT NULL,
  `is_active`     TINYINT(1)  DEFAULT 1,
  `member_count`  INT         DEFAULT NULL COMMENT '该概念冗余字段,成员总数',
  `created_at`    TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    TIMESTAMP   DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`    TINYINT(1)  DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ts_concept_in` (`ts_code`, `concept_code`, `in_date`),
  KEY `idx_concept_active` (`concept_code`, `is_active`),
  KEY `idx_member_count` (`member_count`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC COMMENT='同花顺概念成员拉链表';
```

#### 验收标准（AC）

- **AC1**：member_count 字段可用于过滤
  - **Given** 概念 X 当前成员数 < 10
  - **When** 查询时加 `WHERE member_count >= 10`
  - **Then** 不返回成员过少的概念（消除 PROJECT_OVERVIEW 第 3 节「半数 < 10 只无统计意义」问题）

---

## E3 资金五维补齐（P1）

**Epic 描述**：补齐「主力资金流」维度，对齐 PROJECT_OVERVIEW 第 4 章定义的五维口径。预计耗时 1 工作日。

### E3-S1 建立 `ods_moneyflow`

**作为** L3 资金流计算，**我希望** 拿到个股主力 / 大单 / 中单 / 小单的净流入数据，**以便** 完成「主力」维计算。

#### 任务

- E3-S1-T1 建表 `ods_moneyflow`
- E3-S1-T2 调度时机：17:00（与北向资金同批）
- E3-S1-T3 修正 v0.2 第 5 节标题为「资金五维 = 主力 / 北向 / 两融 / ETF / 龙虎榜」，「大宗交易」「游资席位」归入扩展子项

#### 表结构草案

```sql
CREATE TABLE `ods_moneyflow` (
  `ts_code`         VARCHAR(20)    NOT NULL,
  `trade_date`      DATE           NOT NULL,
  `buy_sm_amount`   DECIMAL(20,2)  COMMENT '小单买入金额(元)',
  `sell_sm_amount`  DECIMAL(20,2),
  `buy_md_amount`   DECIMAL(20,2)  COMMENT '中单',
  `sell_md_amount`  DECIMAL(20,2),
  `buy_lg_amount`   DECIMAL(20,2)  COMMENT '大单',
  `sell_lg_amount`  DECIMAL(20,2),
  `buy_elg_amount`  DECIMAL(20,2)  COMMENT '特大单',
  `sell_elg_amount` DECIMAL(20,2),
  `net_mf_amount`   DECIMAL(20,2)  COMMENT '主力净流入(大+特大)',
  `created_at`      TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`      TINYINT(1)     DEFAULT 0,
  PRIMARY KEY (`ts_code`, `trade_date`),
  KEY `idx_trade_date` (`trade_date`),
  KEY `idx_net_mf` (`trade_date`, `net_mf_amount`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC COMMENT='Tushare 个股资金流(主力大中小单)';
```

#### 验收标准（AC）

- **AC1**：单位统一为元
  - **Given** Tushare `pro.moneyflow()` 返回数据
  - **When** 入库
  - **Then** 所有 amount 字段单位为元（Tushare 原始返回为「万元」，**采集层 `× 10000`**）

- **AC2**：主力净流入字段计算正确
  - **Given** 任一票任一日
  - **When** 查询 `net_mf_amount`
  - **Then** 等于 `(buy_lg + buy_elg) - (sell_lg + sell_elg)`

---

## E4 其他 P1 / P2 漏项

合并处理，按章节追加表清单。每个 Story 不展开 AC，由 Gemini 落地时按 E1 / E2 / E3 模板补 AC。

### E4-S1 停复牌 `ods_suspend_d`（P1）

| 字段 | 类型 | 说明 |
|---|---|---|
| ts_code | VARCHAR(20) | 主键 |
| suspend_date | DATE | 主键，停牌日 |
| resume_date | DATE | 复牌日，NULL=未复牌 |
| suspend_type | VARCHAR(20) | S=停牌 R=复牌 |
| reason | VARCHAR(200) | 停牌原因 |

频率：交易日 16:30。上游：Tushare `pro.suspend_d()`。

### E4-S2 基金净值 `ods_fund_nav`（P1）

| 字段 | 类型 | 说明 |
|---|---|---|
| ts_code | VARCHAR(20) | 主键，基金代码 |
| trade_date | DATE | 主键 |
| unit_nav | DECIMAL(14,4) | 单位净值 |
| accum_nav | DECIMAL(14,4) | 累计净值 |

频率：交易日 19:00（与 ETF 申赎前置）。上游：Tushare `pro.fund_nav()`。**E3 ETF 申赎计算依赖此表**。

### E4-S3 指数权重 `ods_index_weight`（P2）

| 字段 | 类型 | 说明 |
|---|---|---|
| index_code | VARCHAR(20) | 主键 |
| con_code | VARCHAR(20) | 主键，成分股 |
| trade_date | DATE | 主键 |
| weight | DECIMAL(10,6) | 权重(%) |

频率：月更（每月 1 号 07:00）。上游：Tushare `pro.index_weight()`。覆盖沪深 300 / 中证 500 / 上证 50 / 创业板指。

### E4-S4 新股 / IPO 日历 `ods_new_share`（P2）

| 字段 | 类型 | 说明 |
|---|---|---|
| ts_code | VARCHAR(20) | 主键 |
| ipo_date | DATE | 上市日 |
| issue_date | DATE | 发行日 |
| amount | DECIMAL(20,2) | 发行金额 |
| issue_price | DECIMAL(10,2) | 发行价 |

频率：每日 09:00。上游：Tushare `pro.new_share()`。第 9 章事件日历依赖。

### E4-S5 沪深港通持仓 `ods_hsgt_holding`（P2）

| 字段 | 类型 | 说明 |
|---|---|---|
| ts_code | VARCHAR(20) | 主键 |
| trade_date | DATE | 主键 |
| vol | BIGINT | 持股量 |
| ratio | DECIMAL(10,6) | 持股比例(小数) |
| exchange | VARCHAR(10) | SH / SZ |

频率：交易日 19:00。上游：Tushare `pro.hk_hold()`。**TBD：2024-08-19 后是否仍有日终个股数据**（北向盘中已不可用，但日终持仓接口可能还在）。

### E4-S6 股本变动 `ods_share_float`（P2）

| 字段 | 类型 | 说明 |
|---|---|---|
| ts_code | VARCHAR(20) | 主键 |
| ann_date | DATE | 主键 |
| float_share | DECIMAL(20,4) | 流通股本（万股） |
| float_ratio | DECIMAL(10,6) | 流通占比 |
| holder_name | VARCHAR(100) | 解禁股东 |

频率：交易日 18:30。上游：Tushare `pro.share_float()`。

### E4-S7 股权质押统计 `ods_pledge_stat`（P2）

| 字段 | 类型 | 说明 |
|---|---|---|
| ts_code | VARCHAR(20) | 主键 |
| end_date | DATE | 主键，统计截止日 |
| pledge_count | INT | 质押次数 |
| unrest_pledge | DECIMAL(20,4) | 无限售股质押数 |
| pledge_ratio | DECIMAL(10,6) | 质押比例 |

频率：每周五 19:00。上游：Tushare `pro.pledge_stat()`。

---

## 漏项汇总表

| ID | 表名 | 章节 | 优先级 | 频率 | 上游接口 |
|---|---|---|---|---|---|
| 1 | `ods_adj_factor` | 2 (行情) | **P0** | 交易日 16:30 | `pro.adj_factor()` |
| 2 | `dim_sw_industry_member` | 2 (行情) | **P0** | 月更 1 号 06:30 | `pro.index_member_all()` |
| 3 | `dim_concept_member` | 2 (行情) | P1 | 周更 一 06:30 | akshare / 同花顺 |
| 4 | `ods_moneyflow` | 5 (资金) | P1 | 交易日 17:00 | `pro.moneyflow()` |
| 5 | `ods_suspend_d` | 2 (行情) | P1 | 交易日 16:30 | `pro.suspend_d()` |
| 6 | `ods_fund_nav` | 5 (资金) | P1 | 交易日 19:00 | `pro.fund_nav()` |
| 7 | `ods_index_weight` | 7 (跨市场) | P2 | 月更 1 号 07:00 | `pro.index_weight()` |
| 8 | `ods_new_share` | 6 (公告) | P2 | 每日 09:00 | `pro.new_share()` |
| 9 | `ods_hsgt_holding` | 5 (资金) | P2 | 交易日 19:00 | `pro.hk_hold()` |
| 10 | `ods_share_float` | 6 (公告) | P2 | 交易日 18:30 | `pro.share_float()` |
| 11 | `ods_pledge_stat` | 6 (公告) | P2 | 每周五 19:00 | `pro.pledge_stat()` |

**新增 P0：2 张** | **新增 P1：4 张** | **新增 P2：5 张** | **合计 11 张**

合并后 v0.3 总表数 = **38 + 11 = 49 张**

---

## v0.2 备注勘误

| 位置 | 错误描述 | 正确描述 |
|---|---|---|
| 第 2 节 `stock_kline_daily` | 「前复权数据」 | 「不复权原始价；前复权需 JOIN `ods_adj_factor`」 |
| 第 5 节标题 | 「资金五维（北向 / 龙虎榜 / 大宗 / 两融 / ETF / 游资）」(6 项) | 「资金五维（主力 / 北向 / 两融 / ETF / 龙虎榜）」（大宗 / 游资归扩展子项）|

---

## 已产出数据污染评估

### E1-S2 自检结果决定影响范围

**情形 A**：自检发现 `ads_stock_derived_metrics` **未做复权**
- 影响表：`ads_stock_derived_metrics` / `ads_l8_unified_signal` / `ads_l2_style_factor` / `app_anomaly_top10_daily`（历史）
- 处置：补齐 `ods_adj_factor` → ETL 加 JOIN 复权计算 → 历史回灌近 1 年（P0），1-3 年（P1），> 3 年看需求

**情形 B**：自检发现 ETL 用的是 `daily_basic.pct_chg`（Tushare 已修正）
- 影响表：`ads_l8_unified_signal.dist_to_ma20` 等技术指标仍可能有错（如果是自算）
- 处置：聚焦核查 ma_n 类指标的算法

**情形 C**：自检发现 ETL 用了某种隐式复权方式
- 处置：补齐 `ods_adj_factor` 后将 ETL 显式化，避免后续维护风险

---

## 风险与缓解

| 风险 | 影响 | 概率 | 缓解 |
|---|---|---|---|
| 自检确认 `ads_stock_derived_metrics` 未复权 | 近年异动评分 / 风格因子全部错 | 高 | E1 优先级置顶；近 1 年数据立即回灌 |
| 行业成员当前用 `stock_basic_info.industry`（中信） | L2 行业广度系统性偏差 | 中 | E2 同步落地；切换前后做 diff 验证差异范围 |
| `dim_sw_industry_member` 历史拉链初始化困难（早期 Tushare 数据可能缺失） | 历史回算精度受限 | 中 | 接受 2018 年前的行业归属用「最早可得快照」近似，文档显式声明 |
| `ods_hsgt_holding` 2024-08-19 后失效 | E4-S5 接入失败 | 中 | 接入前调用 `pro.hk_hold()` 实测，失败则降级为 P3 不实施 |
| ETF 申赎计算公式 `share_chg × nav × 1e8` 中 nav 用法 TBD | E4-S2 落地后 ETL 仍可能算错 | 低 | 用 `unit_nav` 还是 `accum_nav`，需 Gemini 实施侧明确（见 TBD-C-3）|

---

## 待确认事项（TBD）

| ID | 描述 | 影响 | 优先级 |
|---|---|---|---|
| TBD-C-1 | 自检 SQL 结果：`ads_stock_derived_metrics` 当前是否做了复权？ | 决定历史回灌范围 | **P0** |
| TBD-C-2 | L2 行业广度当前如何获取行业成员？（运行时调 Tushare / `stock_basic_info.industry` / 其他）| 决定 E2 切换风险 | **P0** |
| TBD-C-3 | ETF 申赎计算公式中的 `nav` 用 `unit_nav` 还是 `accum_nav`？ | E4-S2 落地正确性 | P1 |
| TBD-C-4 | `pro.hk_hold()` 在 2024-08-19 后是否仍返回日终个股持仓？ | 决定 E4-S5 是否实施 | P2 |
| TBD-C-5 | 同名概念去重规则（机器人 / 机器人概念 / 人形机器人 三选一保留哪个）| E2-S2 落地 | P2 |
| TBD-C-6 | `dim_sw_industry_member` 历史拉链回溯到哪一年？ | 决定历史回灌窗口 | P2 |

---

## 里程碑

| 里程碑 | 计划日期 | 交付物 |
|---|---|---|
| M1 | TBD+1 工作日 | E1-S2 自检 SQL 结果，确认 ads_* 污染范围 |
| M2 | TBD+2 工作日 | E1-S1 `ods_adj_factor` 采集任务上线，历史回补完成 |
| M3 | TBD+4 工作日 | E2-S1 `dim_sw_industry_member` 上线 + L2 ETL 切换 |
| M4 | TBD+5 工作日 | E3-S1 `ods_moneyflow` 上线，L3 主力维补齐 |
| M5 | TBD+7 工作日 | E4 全部 P1 任务上线（停复牌 / 基金净值 / 概念成员）|
| M6 | TBD+10 工作日 | E4 全部 P2 任务上线，本补遗合并入 v0.3 主文档 |

---

## 度量指标

### 业务指标
- 异动评分修正前后 Top 10 重合度：< 80% 视为「确认有复权污染」
- L2 行业广度切换前后差异：> 5% 视为「确认有中信 / 申万错配」

### 技术指标
- `ods_adj_factor` 日采集行数与 `stock_kline_daily` 差异 < 1%
- `dim_sw_industry_member` 月更后 schema diff 落库时间 < 5 min
- 所有新表 `data_readiness` 写入率 = 100%

---

## 变更记录

| 日期 | 版本 | 变更 | 作者 |
|---|---|---|---|
| 2026-05-12 | v0.2-addendum | v0.2 漏项补遗：11 张表 + 1 处备注修正 + 已产出数据污染评估 | Claude 协助 |
