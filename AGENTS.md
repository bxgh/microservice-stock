# AGENTS.md — A 股盘后系统(腾讯云端仓)实施约束

> 本文件是 Gemini / Antigravity 在本仓实施时**永远生效**的硬约束。任何指令冲突时,本文件的规则**优先于通用最佳实践和 LLM 偏好**。
>
> 设计层文档(`docs/PROJECT_OVERVIEW.md` 等)是 source of truth,本文件只提炼实施侧每行代码都要遵守的规则。

---

## 1. 项目认知

**仓库角色**:本项目是 A 股盘后分析系统的**腾讯云端服务仓**（Tencent Cloud Environment）。

- 数据上游:Tushare / AkShare / BaoStock 等三方 API
- 本仓职责:负责数据采集、数据就绪探测(Readiness Probing)、任务状态监控、对外 API 提供
- 开发边界:**只负责云端逻辑,严禁混淆物理边界。**内网服务器(如 Node-41 / stock-compute)为下游逻辑,本仓仅通过指令队列做接力。
- 设计 source of truth:`docs/PROJECT_OVERVIEW.md` / `docs/TABLES_INDEX.md`

**协作分工**:
- 设计在 Claude(Anthropic), 交付为 Markdown 文档 (Epic-Story-Task-AC 结构)。
- **文档归口原则**: 
  - 全局架构类设计存放于根目录 `docs/`。
  - **微服务专属设计与实施文档** (含 Epic/Story/Plan/Task) **必须** 存放于该服务目录下的 `docs/` 中。
- **实施日志路径**: 必须按照设计文档同目录下的 `implementation_logs/E{N}/S{M}/` 文件夹进行物理存证。

> [!IMPORTANT]
> **文档归口原则**: 严禁在根目录 `docs/` 存放微服务专属的开发设计文档。针对 `scf-collector`, `tushare-api` 等微服务的所有 Epic/Story 设计及实施日志，**必须** 物理存放于该微服务根目录下的 `docs/` 文件夹中。

---

## 2. 技术栈与编码标准 (Modular)

本仓实施模块化标准治理。通用编码规约已下沉至专职规约文件，Agent 在开发时必须实时对齐。

- **通用编码规约**: [python-coding-standards.md](file:///home/ubuntu/microservice-stock/.agent/rules/python-coding-standards.md) (包含 Async, 锁机制, 熔断与重试等)
- **数据库约束**: **MySQL 5.7**(不是 8.0)+ ClickHouse(双写)
- **调度规范**: APScheduler + 自研 JSON pipeline。任务完成/失败必须触发标准邮件报告。
- **DDL 管理**: 所有 schema 变更进 `migrations/`, **禁止内嵌业务代码**。

---

## 3. 命名规范与结构门禁 (强制)

### 3.1 表前缀与字段审计

本仓由 `.agents/scripts/` 下的自动化审计脚本强制执行以下规范：

- **表前缀**: `ods_` (原始), `dwd_` (明细), `ads_` (应用), `meta_` (系统) 等。
- **字段门禁**: `ts_code`, `trade_date`, `pct_chg` (小数), `amount` (元)。
- **尾部三件套**: 每张新表必须包含 `created_at`, `updated_at`, `is_deleted` 及其索引。

### 3.2 根目录整洁规范 (Strict Root Dir Governance)

**核心原则**: 根目录必须保持绝对精简。严禁在根目录新建任何临时、调试或一次性文件。

1. **白名单准入**: 根目录仅允许存在核心工程目录 (`akshare-api/`, `baostock-api/`, `stock-manager-api/`, `monitor-service/`, `pywencai-api/`, `tushare-api/`, `wxch-gateway/`, `stock-compute/`, `docs/`, `scripts/`, `migrations/`, `tests/`, `logs/`, `.agent/`, `.agents/` 等) 及核心配置文件 (`AGENTS.md`, `CLAUDE.md`, `README.md`, `PIPELINE_EVENT_API.md`, `docker-compose.yml`, `.env`, `.env.example`, `.gitignore` 等)。
2. **日志重定向**: 严禁在根目录生成 `.log` 或 `.out` 文件。
3. **临时文件物理隔离**: 
   - 微服务内测试代码存放在该服务下的 `scratch/`。
   - 跨模块脚本必须存放在 `scratch/history/`。

> [!CAUTION]
> **强力审计**: Agent 严禁在根目录创建任何不在白名单内的文件。提交 PR 前必须执行物理清理。

---

## 4. 业务领域口径 (A 股专属)

本仓处理采集与 API 交付，需严格遵循以下业务口径：
- **涨跌停**: 全部按主板 9.7% 简化判定。
- **北向资金**: 2024-08-19 后个股北向数据已停发，严禁编造或引用。
- **单位陷阱**: ETF 净申购金额必须乘 `1e8`。
- **交易日历**: 必须使用 `meta_trading_calendar` 跳转，严禁日历日加减。

---

## 5. 文档协作与“真源”准则 (Epic-Story-Task-AC)

### 5.1 实施前准入 (Readiness Check)
在正式开始任何 Story 的开发前，必须在 `implementation_plan.md` 中完成认证：
- [ ] **需求解析**: 3句话描述核心逻辑。
- [ ] **依赖认证**: 查实 `TABLES_INDEX.md` 及环境连通性。
- [ ] **角色激活**: 显式声明激活的角色（参考 `docs/architecture/agent-skill-rules/ROLES.md`）。

### 5.2 实施过程规范
1. **禁止无文档开发 (Docs-First)**: 严禁未经本地 `implementation_plan.md` 和 `task.md` 存证直接编写代码。
2. **Task ID 进 Commit**: 每个 Task 对应一个 Commit，前缀 `[E1-S1-T1]`。
3. **验收前必跑 AC**: 所有验收标准 (AC) 必须转为可执行测试。

### 5.3 验证“真源”准则
- **物理查验**: 必须通过 `docker exec` 或 SQL 直连数据库确认真实记录，严禁盲目信任 API 返回值。
- **存证要求**: `walkthrough.md` 必须包含真实的 SQL 结果块或日志片段。
- **交付物闭环**: 每一项 Story (S) 开发完成后，必须在对应的 `implementation_logs/E{N}/S{M}/` 目录下生成 `REPORT.md` (技术报告) 及 `API.md` (如有接口变更)。

### 5.4 数据质量闭环 (QC Feedback Loop)

1. **映射双检**: 所有 `ods_` 层接入必须输出“字段对齐矩阵”脚本及结果。
2. **灰度先行**: 历史同步必须遵循 `10只股票样本 -> 校验 -> 全量回填` 的三段式流程。
3. **空值红线**: 核心字段（Fact）在回填结束后必须执行 `COUNT(*) WHERE IS NULL` 审计。

---

## 6. 反模式清单 (自检)

- ❌ 字段命名用 `stock_code` / `dt` (应为 `ts_code` / `trade_date`)
- ❌ `pct_chg` 当百分比处理 (应为小数)
- ❌ 漏掉 `is_deleted = 0` 过滤
- ❌ **在根目录随意创建测试文件**
- ❌ **在云端执行耗时计算** (应转发至内网 Node-41)
- ❌ **外部 API 调用缺失熔断/重试机制**
- ❌ **使用硬编码 Cron 触发盘后任务** (应接入 WorkflowManager 事件流)
- ❌ **网关暴露敏感堆栈信息** (应在 wxch-gateway 实现错误脱敏)
- ❌ TBD 字段用编造值填补
- ❌ 未经本地文档化（Plan/Task）直接编写代码

---

**变更记录**

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-05-06 | v0.1 | 初版 |
| 2026-05-08 | v0.8 | 增加“严禁跨任务开发”与交付完备性要求。 |
| 2026-05-09 | v1.2 | **架构重构**: 引入虚拟角色体系，技术标准下沉至 python-coding-standards.md，建立根目录整洁白名单。 |
| 2026-05-10 | v1.3 | **环境对齐**: 修正“核心禁令”中关于 Node-41 和 Gost 隧道的错误描述，明确腾讯云环境约束。 |
| 2026-05-10 | v1.4 | **质量对齐**: 建立 5.4 节数据质量闭环，强化 [Data Quality Steward] 约束。 |
| 2026-05-10 | v1.5 | **交付对齐**: 强化 5.3 节，要求每个 Story 必须产出 REPORT.md 和 API.md 存证。 |
| 2026-05-12 | v1.6 | **文档归口**: 明确微服务专属设计与实施文档需存放在服务内部的 `docs/` 目录下。 |
