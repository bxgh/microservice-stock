# Epic: E300 - A 股盘后数据采集验证系统 (Data Ingestion Verification)

> **Status**: In-Progress  
> **Source of Truth**: [E300_Data_Ingestion_Verification.md](file:///home/ubuntu/microservice-stock/docs/design/数据管线/E300_Data_Ingestion_Verification.md)

## 1. 背景与目标

### 1.1 背景
随着 `data_update_schedule.md` (v0.2) 的补全，采集系统已覆盖 L1-L7 共计 20+ 张原始数据表 (`ods_*`)。目前采集逻辑分散在各微服务中，缺乏统一的接口契约校验和数据质量审计手段。
由于 A 股数据上游（Tushare/AkShare）存在字段变更、数据污染（如百分比与小数混用）、延迟发布等风险，急需建立一套标准化的验证体系。

### 1.2 目标
- **字段契约认证**：确保所有采集表与上游接口字段 100% 对齐。
- **采集时序验证**：验证各表采集耗时及就绪时间是否满足盘后流水线死线。
- **数据质量闭环**：实现自动化的“空值红线”和“量纲陷阱”审计。
- **跨源比对方案**：针对 P0 级表建立 Tushare 与 AkShare 的一致性校验。

### 1.3 验证范围 (Target Tables)

根据 `data_update_schedule.md` (v0.2)，本项目涉及以下 30+ 张表的采集验证：

| 章节 | 类别 | 目标表 (ods_ / dim_ / meta_) |
|---|---|---|
| 元数据 | 系统 | `dim_stock_basic`, `meta_trading_calendar`, `meta_data_readiness` |
| 行情 | L1/L2 | `stock_kline_daily`, `ods_index_daily`, `daily_basic`, `ods_event_limit_pool`, `ods_sw_index_daily`, `ods_concept_kline_daily`, `ods_market_breadth_daily` |
| 财务 | 基本面 | `stock_balance_sheet`, `stock_income_statement`, `stock_cash_flow_statement`, `stock_finance_indicators`, `stock_shareholder_count`, `stock_top10_shareholders` |
| 资金 | L3 | `stock_north_funds_daily`, `north_capital_daily`, `stock_lhb_daily`, `stock_lhb_stock`, `stock_block_trade`, `ods_margin_total`, `ods_margin_detail`, `ods_etf_share_chg` |
| 公告 | L6 | `ods_holdertrade`, `ods_repurchase`, `ods_dividend`, `ods_st_change`, `ods_investigation`, `ods_forecast`, `ods_express`, `ods_share_release`, `ods_announcement` |
| 跨市场 | L7 | `ods_index_global_daily` |
| 情绪 | L4 | `monitor_indicators_history` |

---

## 2. 角色激活
- [Project Manager]: 负责 Story 规划与业务口齐对齐。
- [Python Backend Engineer]: 负责验证脚本编写与 API 接入。
- [Data Quality Steward]: 负责审计规则制定与 QC 报告生成。

---

## 3. 实施计划 (Stories)

### E300-S1: ODS 层字段对齐与 Mapping 矩阵认证
**描述**：针对 `data_update_schedule.md` 中定义的全部 20+ 张表，输出“字段对齐矩阵”，并编写自动化脚本验证上游接口返回结构与 DB Schema 是否一致。

#### 任务
- [ ] T1: 编写 `field_mapping_audit.py` 脚本，动态获取接口返回 header 并与 `TABLES_INDEX.md` 对齐。
- [ ] T2: 逐表验证「单位陷阱」（如成交额单位元、涨跌幅小数化）。
- [ ] T3: 生成 `REPORT.md`，记录所有字段映射的差异及处理逻辑（如 `/100` 或 `*1e8`）。

#### 验收标准 (AC)
- **Given**: `TABLES_INDEX.md` 中定义的表结构。
- **When**: 运行采集验证脚本。
- **Then**: 脚本必须输出 Pass/Fail 矩阵，任何字段缺失或类型不匹配均需报警。

### E300-S2: 采集就绪度 (Readiness) 与时效性压力测试
**描述**：模拟盘后高并发采集场景，验证各表从触发到写入 `data_readiness` 的耗时，并核实是否满足 17:00/18:00 等关键时点。

#### 任务
- [ ] T1: 编写性能分析装饰器，记录每次采集的 `start_at`, `end_at`, `row_count`。
- [ ] T2: 验证 `data_readiness` 写入机制是否严格遵循 P3 契约。
- [ ] T3: 针对 `stock_kline_daily` (1200w+) 进行增量同步压力测试，确保在 15 分钟内完成。

#### 验收标准 (AC)
- **Given**: 交易日 16:30 后的真实环境。
- **When**: 触发全量采集任务。
- **Then**: 17:00 前 P0 级数据必须全部标记为 `ready`，平均耗时记录在案。

### E300-S3: 数据质量 (QC) 自动化审计桩
**描述**：在采集流水线中植入 QC 检查桩，对核心字段（Fact）执行空值、零值、范围异常审计。

#### 任务
- [ ] T1: 实现 `qc_feedback_loop` 装饰器，集成至所有 `ods_*` 采集函数。
- [ ] T2: 编写针对 `pct_chg` 的范围检查规则（主板 > 0.11 或 < -0.11 自动拦截）。
- [ ] T3: 实现 `COUNT(*) WHERE IS NULL` 审计，结果自动存入 `dq_findings` 表。

#### 验收标准 (AC)
- **Given**: 采集入库后的数据集。
- **When**: 执行 QC 审计脚本。
- **Then**: 核心字段空值率必须为 0，异常值需触发 P1 级邮件告警。

### E300-S4: P0 级表多源一致性 (Consensus) 抽样校验
**描述**：针对 `stock_kline_daily` 和 `ods_event_limit_pool` 等 P0 表，同时拉取 Tushare 和 AkShare 数据进行 1% 样本比对。

#### 任务
- [ ] T1: 实现跨源比对引擎，支持指定 `ts_code` 和 `trade_date` 的深度比对。
- [ ] T2: 编写抽样逻辑，每日随机抽取 50 只股票验证开高低收及成交额一致性。
- [ ] T3: 针对龙虎榜（AkShare 备源）进行字段对齐。

#### 验收标准 (AC)
- **Given**: 两套数据源的返回结果。
- **When**: 运行一致性校验。
- **Then**: P0 表的数值误差需控制在 10^-6 以内，若出现重大分歧需触发 P0 级告警。

---

## 4. 交付物清单
1. **Epic 文档**: `docs/epics/Epic-Data-Ingestion-Verification.md` (即本文件)
2. **实施日志**: `implementation_logs/E300/S1/REPORT.md` 等
3. **验证脚本**: `scripts/validation/field_mapping_audit.py`
4. **API 文档**: `docs/api/data-validation-api.md`
