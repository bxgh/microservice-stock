# PRD: E7 数据管线全链路 Serverless 迁移与集成 (Full-Chain Serverless Pipeline)

> **版本**: v1.0 (Draft)
> **状态**: 规划中
> **Epic ID**: E7
> **目标**: 实现从“基于时间的串行 CVM 脚本”向“基于事件的并行 SCF 微服务矩阵”的全面跨越。

---

## 1. 项目背景与目标

### 1.1 背景
当前 `scf-collector` 已实现基础日线行情的多源容错采集，但量化决策所需的复权因子、估值指标及元数据仍残留在旧的 CVM (Node-41) 环境中。

### 1.2 核心目标
1. **全链路覆盖**：将复权因子、交易日历、股票列表等全量迁移至云端。
2. **事件驱动**：废除 Cron 定时死等，通过 `meta_pipeline_run` 驱动下游接力。
3. **弹性扩展**：支持 Meta 同步、Daily 采集、Finance 抓取的物理隔离与独立部署。

---

## 2. 核心设计原则

- **Doc-First**: 所有变更先有 PRD 和状态机设计，后有代码。
- **Gate-Keep**: 下游任务（指标计算）必须验证 `meta_data_readiness` 契约。
- **Atomic Relay**: 每一个采集节点成功后，必须主动上报状态并尝试触发接力（Relay）。

---

## 3. 功能需求 (User Stories)

### ### E7-S1: 基础元数据云端同步 (Meta Foundation)
**目标**: 剥离低频任务，建立云端“真源”基础。
- **AC1 (Calendar)**: 每日 08:30 自动同步 Tushare 交易日历，更新 `trade_cal` (保持物理表名不变)。
- **AC2 (StockList)**: 每日 09:00 同步全市场股票列表 (目标表 `stock_basic_info`)、行业分类、退市状态。
- **AC3 (Isolation)**: 作为一个独立的 SCF (`stock-scf-meta`) 运行。

### ### E7-S2: 深度行情与复权因子扩展 (Data Enrichment)
**目标**: 补全 K 线数据的“灵魂”。
- **AC1 (Adj Factor)**: Tushare Collector 必须在盘后同步抓取 `adj_factor`（复权因子）。
- **AC2 (Basic Info)**: 补全 `turnover` (换手率)、`pe` (市盈率)、`pb` (市净率)、`total_mv` (总市值)。
- **AC3 (Integrity Check)**: 只有当 Price、Volume、Adj_Factor 三者均不为空时，才标记该股票当日数据“就绪”。

### ### E7-S3: 云端状态机与跨网接力 (State Machine & Handover)
**目标**: 自动化完成“云端采集 -> 内网计算”的闭环。
- **AC1 (Pipeline Run)**: 引入 `PipelineTracker` 模块，采集开始记录 `RUNNING`，结束记录 `COMPLETED`。
- **AC2 (Handover Gateway)**: 采集完成后，SCF 主动向 `wxch-gateway` 发起指令请求。
- **AC3 (Gate-3 Compliance)**: 只有 `meta_data_readiness` 中 `status='READY'` 时，才下发下发指令给内网计算节点。

---

## 4. 关键数据合约 (Data Contracts)

### 4.1 任务审计表 (`meta_pipeline_run`)
| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `pipeline_id` | VARCHAR | 任务唯一 ID (如 `daily_collection_20260512`) |
| `status` | VARCHAR | `RUNNING`, `COMPLETED`, `FAILED`, `DEGRADED` |
| `collector_source` | VARCHAR | 最终成功的数据源 (Tushare/Akshare/EasyQuotation) |
| `record_count` | INT | 实际采集入库的股票条数 |

### 4.2 就绪状态表 (`meta_data_readiness`)
| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `table_name` | VARCHAR | `ods_stock_daily` |
| `biz_date` | DATE | 交易日期 |
| `status` | VARCHAR | `READY` (表示该表该日数据已完全就绪) |

---

## 5. 迁移实施路径 (Roadmap)

1. **Phase 1 (基础)**: 建立 `scf-meta`，确立交易日历基准。
2. **Phase 2 (扩展)**: 升级 `scf-collector` 采集逻辑，支持复权因子和基础估值指标。
3. **Phase 3 (闭环)**: 注入状态机逻辑，打通向内网下发指令的 Webhook 链路。

---
**备案信息**
- **设计者**: Antigravity AI
- **关联 Epic**: E7
- **存证路径**: `scf-collector/docs/PRD_E7_SERVERLESS_PIPELINE.md`
