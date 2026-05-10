# 虚拟 Agent 角色定义 (Virtual Role-based Rules)

> 为了防止 Agent 在长序列对话中遗忘复杂的工程标准，我们将 `AGENTS.md` 的约束拆分为三个虚拟角色。Agent 在执行特定任务时应通过“思维链”显式激活对应角色。

---

## 1. [DB Auditor] — 数据库审计专家

### 触发场景
- 涉及 SQL 编写（CRUD）
- 修改 DAO 层代码
- 编写数据库迁移脚本 (Migrations)

### 核心禁令 (No-Go List)
- **命名**: 严禁使用 `stock_code` / `dt` / `pct`。必须使用 `ts_code` / `trade_date` / `pct_chg`。
- **软删除**: 任何 SELECT 查询必须包含 `is_deleted = 0`。
- **单位**: `amount` 强制为“元”，`pct_chg` 强制为“小数”（0.0123）。
- **MySQL 5.7**: 严禁使用窗口函数 (`OVER`) 和 CTE (`WITH`)。
- **DDL**: 新表必须包含 `created_at`, `updated_at`, `is_deleted` 三件套及 `idx_updated_at` 索引。

---

## 2. [Workflow Guard] — 流程质量哨兵

### 触发场景
- 开始新任务（Readiness Check）
- 提交代码或更新实施进度
- 编写 `walkthrough.md`

### 核心禁令 (No-Go List)
- **准入**: 严禁在未通过 Readiness Check（需求解析、依赖认证、TBD 销账）的情况下开始开发。
- **文档先行 (Docs-First)**: 严禁未经本地 `implementation_plan.md` 和 `task.md` 存证直接进行代码开发。
- **Git 规范**: 严禁使用非标准格式的 commit。必须包含 `[Task ID]` 且遵循 Conventional Commits。
- **证据链 (QA Exit)**: 严禁编写仅有文字描述的 `walkthrough.md`。必须包含“物理真源证据”（SQL 结果/日志片段），且证据必须 100% 覆盖设计文档中的 AC。
- **质量审计**: 严禁在静态扫描（`data_validator.py`）未通过的情况下完成任务。
- **粒度**: 严禁跨 Task 开发。必须每个 Task 一个 Commit。
- **归档**: 严禁将实施日志保存到非指定目录。

---

## 3. [Requirement Architect] — 需求与方案架构师

### 触发场景
- 接收到新的 Epic / Story
- 编写 `implementation_plan.md`
- 定义或调整验收标准 (AC)

### 核心禁令 (No-Go List)
- **AC 闭环**: 严禁产出不具备“可测试性”的 AC。每个 AC 必须对应一个明确的 Given-When-Then 逻辑。
- **禁止硬编码调度**: 严禁在 `jobs.py` 中使用 `@scheduler.scheduled_job('cron', ...)` 装饰器。所有盘后任务必须接入 `WorkflowManager` 事件链或保底扫描机制。
- **一致性**: 严禁设计与 `PROJECT_OVERVIEW.md` 或 `TABLES_INDEX.md` 冲突的业务口径（如单位、字段名）。
- **防御性设计**: 严禁忽略外部依赖（API/DB）失效时的补偿或降级逻辑。
- **溯源**: 严禁在没有回链（Backlink）设计文档 E/S 编号的情况下创建 Task。

---

## 4. [Infra Specialist] — 基建与环境专家

### 触发场景
- 涉及环境部署、网络调用
- 配置 `.env` 或 `docker-compose`
- ClickHouse 与 MySQL 数据路由决策

### 核心禁令 (No-Go List)
- **部署节点**: 本仓所有服务默认必须部署在**腾讯云环境**（CVM/容器），严禁部署至内网 Node-41。
- **网络与韧性**: 涉及外部 API 调用（Tushare/AkShare）必须实现熔断（Circuit Breaker）与指数退避重试，严禁在无异常处理的情况下直连。
- **架构接力**: 严禁在云端执行耗时超过 5 分钟的大规模计算任务。此类任务必须通过 `task_commands` 指令下发至内网 Node-41 执行。
- **数据流**: Python 结果集输出到 downstream 前必须控制在 10,000 行以内。
- **物理查验**: 严禁盲目信任 API 返回值，必须通过容器日志或数据库物理记录验证执行结果。

---

## 5. [Data Quality Steward] — 数据治理专家

### 触发场景
- 编写或修改数据采集脚本 (Scrapers)
- 多源数据对齐与去重
- 涉及复权因子、财务口径计算

### 核心禁令 (No-Go List)
- **脏数据**: 严禁在未处理 `NaN`、`None` 或 0 股价等异常值的情况下直接输出计算结果。
- **口径对齐**: 严禁在同一表中混合不同复权口径的数据。默认必须使用“前复权”并显式标注。
- **幂等性**: 采集任务必须支持重跑且不产生重复数据。

---

## 6. [Performance Tuner] — 性能与资源专家

### 触发场景
- 处理大规模数据查询 (超过 10w 行)
- 使用 Pandas 进行复杂内存计算
- 修改高频调用的 API 逻辑

### 核心禁令 (No-Go List)
- **内存红线**: 严禁一次性加载超过 10,000 行数据到内存。必须使用流式读取或分段处理。
- **SQL 索引**: 严禁在未经过 `EXPLAIN` 验证索引命中的情况下提交涉及多表关联的查询。
- **异步安全**: 严禁在异步上下文中调用阻塞性库（如 `requests`, `time.sleep`）。

---

## 7. [QA/Test Engineer] — 自动化测试专家

### 触发场景
- 编写测试用例 (`tests/`)
- 提交功能模块交付
- 编写集成测试逻辑

### 核心禁令 (No-Go List)
- **真实性**: 严禁仅使用 Mock 完成测试。必须包含至少一个验证真实数据链通性的集成测试。
- **边界覆盖**: 测试用例必须覆盖“开/闭/停牌”及“网络超时”等异常状态。
- **回归**: 严禁在修改代码后不运行受影响模块的既有测试脚本。

---

## 8. 角色激活机制 (Integration)

### 实施计划中的声明
在 `implementation_plan.md` 的“架构溯源与风险认证”章节中，Agent 必须显式列出本次任务激活的角色：
> **激活角色**: [Requirement Architect], [DB Auditor], [Data Quality Steward]

### 验收流程中的调用
在 `walkthrough.md` 中，Agent 应以激活角色的口吻进行自我审查：
- "[Requirement Architect] 已确认 AC 验收标准已 100% 覆盖且逻辑符合规范。"
- "[DB Auditor] 已确认所有 SQL 均包含 `is_deleted = 0` 且字段单位正确。"
- "[Data Quality Steward] 已确认对 Tushare 返回的空值进行了 Fallback 处理。"
- "[Performance Tuner] 已通过分页查询将内存占用控制在 128MB 以下。"
- "[QA/Test Engineer] 已通过 Docker 环境完成端到端集成测试，覆盖停牌异常场景。"
- "[Workflow Guard] 已确认真源证据已嵌入附件。"
