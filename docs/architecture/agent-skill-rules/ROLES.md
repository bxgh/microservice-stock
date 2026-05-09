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

## 3. [Infra Specialist] — 基建与环境专家

### 触发场景
- 涉及环境部署、网络调用
- 配置 `.env` 或 `docker-compose`
- ClickHouse 与 MySQL 数据路由决策

### 核心禁令 (No-Go List)
- **部署节点**: 所有服务默认必须部署在 Node-41。
- **网络**: 涉及外部 API 调用必须配置 Gost 隧道或代理，否则视为 Bug。
- **数据流**: Python 结果集输出到下游前必须控制在 10,000 行以内。
- **架构**: 严禁盲目信任 API 返回值，必须通过容器日志追踪底层错误。

---

## 4. 角色激活机制 (Integration)

### 实施计划中的声明
在 `implementation_plan.md` 的“架构溯源与风险认证”章节中，Agent 必须显式列出本次任务激活的角色：
> **激活角色**: [DB Auditor], [Workflow Guard]

### 验收流程中的调用
在 `walkthrough.md` 中，Agent 应以激活角色的口吻进行自我审查：
- "[DB Auditor] 已确认所有 SQL 均包含 `is_deleted = 0` 且 `amount` 单位为元。"
- "[Workflow Guard] 已确认真源证据已嵌入附件，且 Git 提交遵循标准格式。"
- "[Workflow Guard] 已确认静态扫描 `.agents/scripts/data_validator.py` 结果为 0 违规。"
