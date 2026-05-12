# Epic: E400 - SCF 高可靠数据采集体系补全 (SCF Collector Implementation)

> **Status**: Designing  
> **Source of Truth**: [E400_SCF_Collector_Implementation.md](file:///home/ubuntu/microservice-stock/docs/design/SCF/E400_SCF_Collector_Implementation.md)

## 1. 背景与目标

### 1.1 背景
当前 `scf-collector` 已完成元数据（交易日历、股票列表）的同步逻辑，并具备基础的 VPC 穿透与云端部署能力。然而，核心的行情数据（K 线）、财务基本面、资金流及公告事件等 30+ 张表尚未实现生产级的自动化采集。

### 1.2 目标
- **全量补全**：实现 `todo-list-tables.md` (含 v0.2 补遗) 中定义的 49 张表的采集逻辑。
- **存量兼容**：开发前必须物理核对 MySQL 存量数据（E300 报告），严禁盲目新建同类表。
- **高可靠性**：支持 3 次指数退避重试、连接池自愈及 256MB 内存红线控制。
- **规格对齐**：物理落库字段 100% 对齐 `TABLES_INDEX.md`，规避量纲陷阱（元/小数）。
- **信号驱动**：采集完成后自动更新 `meta_data_readiness`，打通盘后流水线事件链。

### 1.3 表名决策与存量对齐 (Decision Matrix)
根据 `AGENTS.md` 规范与当前数据库实际情况，本 Epic 对采集表名进行以下销账：

**存量表 (Legacy - 保持现状)**:
- 核心行情: `stock_kline_daily` (不复权)
- 复权因子: `stock_adjust_factor`
- 业绩预告: `stock_performance_forecast`
- 限售解禁: `stock_restricted_release`
- 停复牌: `stock_suspensions`

**新增表 (New - 采用 ods_ 前缀)**:
- `ods_sw_index_daily`: 申万行业指数 (已存在)
- `ods_lhb_detail`: 龙虎榜个股明细 (区别于 `stock_lhb_daily` 统计)
- `ods_margin_market`: 市场级融资融券
- `ods_margin_detail`: 个股级融资融券
- `ods_etf_holder_chg`: ETF 份额变动
- `ods_stk_express`: 业绩快报
- `ods_stk_announcement`: 公告主表
- `dim_sw_industry_member`: 申万行业成员拉链表

---

## 2. 实施计划 (Stories)

### E400-S1: P0 核心行情同步 (Daily K-Lines)
**描述**：正式实现个股及指数的日 K 线同步，作为全系统的 P0 级数据源。

#### 任务 (Tasks)
- [ ] T1: 实现 `sync_kline_daily` (存量表 `stock_kline_daily`) 核心函数，支持 `vol` -> `volume` 字段对齐。
- [ ] T2: **[P0]** 实现 `sync_adj_factor` (存量表 `stock_adjust_factor`) 采集。
- [ ] T3: **[P0]** 实现 `sync_sw_industry_member` (新增维表 `dim_sw_industry_member`) 消除 Schema 漂移。
- [ ] T4: 实现 `sync_index_daily` 与 `sync_sw_index_daily` (已存在 `ods_sw_index_daily`)。
- [ ] T5: 集成 `StockDAO.update_data_readiness` 信号机制。

#### 验收标准 (AC)
- **Given**: Tushare Pro 积分充足且交易日已收盘。
- **When**: 触发 `op=sync_kline_daily` 任务。
- **Then**: 5000+ 股票 K 线需在 15 分钟内入库，且 `meta_data_readiness` 标记为 `READY`。

---

### E400-S2: P1 估值指标与异动探测 (Daily Indicators)
**描述**：采集每日 PE/PB 估值及涨跌停原因，支撑策略选股。

#### 任务 (Tasks)
- [ ] T1: 实现 `sync_daily_basic` (存量表 `daily_basic`) 接口，处理量纲转换。
- [ ] T2: 实现 `sync_limit_pool` (存量表 `ods_event_limit_pool`)。
- [ ] T3: **[NEW]** 实现 `sync_fund_nav` (基金净值) 与 `sync_suspensions` (存量表 `stock_suspensions`)。
- [ ] T4: **[NEW]** 实现 `sync_concept_member` (概念成员归属)。
- [ ] T5: 编写对应的 Pydantic 模型确保数据校验。

#### 验收标准 (AC)
- **Given**: 交易日 16:00 后。
- **When**: 触发同步任务。
- **Then**: `daily_basic` 表中所有股票的 `pe_ttm`, `turnover_rate` 等字段非空。

---

### E400-S3: P2 财务报表与股东结构 (Fundamentals)
**描述**：补全三大会计报表及十大股东数据，处理季度性大批量同步。

#### 任务 (Tasks)
- [ ] T1: 实现 `stock_balance_sheet`, `stock_income`, `stock_cashflow` 的流式采集。
- [ ] T2: 实现 `top10_holders` 及股东户数抓取。
- [ ] T3: 针对报表发布期的重叠日期执行幂等去重。

#### 验收标准 (AC)
- **Given**: 财报披露季。
- **When**: 执行财务同步任务。
- **Then**: SCF 内存占用不得超过 256MB，单次同步无超时。

---

### E400-S4: P3 资金流与公告事件 (Capital Flows & Events)
**描述**：补全龙虎榜、两融、北向资金及业绩预告等辅助决策数据。

#### 任务 (Tasks)
- [ ] T1: **[NEW]** 实现 `sync_moneyflow` (存量表 `ods_moneyflow`) 补全主力维。
- [ ] T2: 实现 `sync_lhb_detail` (新增 `ods_lhb_detail`) 与 `ods_margin_detail`。
- [ ] T3: 实现 `sync_hsgt_holding` (存量表 `stock_north_funds_daily` 或新增 `ods_hsgt_holding`)。
- [ ] T4: 实现 `sync_performance_forecast` (存量表 `stock_performance_forecast`) 与 `stock_restricted_release` 同步。

#### 验收标准 (AC)
- **Given**: 交易日 20:00 后。
- **When**: 触发资金流同步。
- **Then**: 相关 `ods_*` 表增量数据入库，`is_deleted` 默认为 0。

---

## 3. 交付物清单
1. **Epic 文档**: `docs/epics/Epic-SCF-Collector-Implementation.md` (本文件)
2. **实施存证**: `implementation_logs/E400/S{N}/walkthrough.md`
3. **API 规范**: `docs/api/scf-collector-api.md`
4. **数据库变更**: `migrations/E400_create_ods_tables.sql`
