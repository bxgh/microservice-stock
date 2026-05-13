# 虚拟 Agent 角色定义 (Virtual Role-based Rules)

> 为了防止 Agent 在长序列对话中遗忘复杂的工程标准，我们将 `AGENTS.md` 的约束拆分为多个虚拟角色。Agent 在执行特定任务时应通过“思维链”显式激活对应角色。

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
- **MySQL 5.7**: 严禁使用窗口函数 (`OVER`) 和 CTE (`WITH`)。执行 `ON DUPLICATE KEY UPDATE` 时，必须显式更新 `updated_at = CURRENT_TIMESTAMP`，否则值未变时该字段不会自动触发。
- **老表防御**: 严禁在老表（如 `stock_basic_info`）查询中盲目添加 `is_deleted` 过滤，除非已通过 `DESCRIBE` 物理确认字段存在。
- **DDL**: 新表必须包含 `created_at`, `updated_at`, `is_deleted` 三件套及 `idx_updated_at` 索引。

---

## 2. [Backend Engineer] — 后端工程专家

### 触发场景
- 编写业务逻辑代码 (Business Logic)
- 定义 Pydantic 模型、FastAPI 路由或中间件
- 封装通用工具类 (Utils) 或装饰器
- 处理异步并发逻辑 (Async/Await)

### 核心禁令 (No-Go List)
- **异步阻塞**: 严禁在异步上下文中使用 `requests`、`time.sleep` 或任何同步阻塞的 IO 库。
- **并发安全**: 严禁在操作共享可变状态（如内存缓存）时忽略 `asyncio.Lock()`。
- **资源闭环**: 严禁在调用外部 I/O 时忽略 `try...finally` 或 `async with` 资源回收逻辑；在 SCF 环境下，严禁在每次方法调用中重复初始化 API Client（如 `pro_api`），必须在构造函数中持久化复用。
- **模型严谨性**: 严禁在 Pydantic 模型中使用 `Any` 或未定义验证规则的字段；严禁绕过模型校验直接处理原始 Dict。
- **硬编码**: 严禁在任何代码（含 `scratch/` 脚本）中硬编码数据库密码或 API Token，必须统一通过 `os.getenv` 读取。
- **错误脱敏**: 严禁在 API 响应中透传原始 Traceback 或底层异常信息，必须封装为标准错误响应。

---

## 3. [Workflow Guard] — 流程质量哨兵

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
- **安全性**: 严禁提交任何未被 `.gitignore` 排除且含有本地敏感配置的 `scratch/` 脚本。
- **粒度**: 严禁跨 Task 开发。必须每个 Task 一个 Commit。
- **归档**: 严禁将实施日志保存到非指定目录。

---

## 4. [Requirement Architect] — 需求与方案架构师

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

## 5. [Infra Specialist] — 基建与环境专家

### 触发场景
- 涉及环境部署、网络调用
- 配置 `.env` 或 `docker-compose`
- ClickHouse 与 MySQL 数据路由决策

### 核心禁令 (No-Go List)
- **部署节点**: 本仓所有服务默认必须部署在**腾讯云环境**（CVM/容器），严禁部署至内网 Node-41。
- **网络与韧性**: 涉及外部 API 调用（Tushare/AkShare）必须实现熔断（Circuit Breaker）与指数退避重试，严禁在无异常处理的情况下直连。
- **架构接力**: 严禁在云端执行耗时超过 5 分钟的大规模计算任务。此类任务必须通过 `task_commands` 指令下发至内网 Node-41 执行。
- **数据流**: Python 结果集输出到 downstream 前必须控制在 10,000 行以内。
- **空值日志**: 严禁在接口返回空结果（如非交易日请求）时静默退出，必须增加明确的日志说明以区分“系统故障”与“正常空态”。
- **物理查验**: 严禁盲目信任 API 返回值，必须通过容器日志或数据库物理记录验证执行结果。
- **WXCH 适配**: 在微信云托管环境部署时，严禁硬编码 DB 连接 IP，必须使用云托管控制台注入的环境变量及内网域名。

---

## 6. [Data Quality Steward] — 数据治理专家

### 触发场景
- 编写或修改数据采集脚本 (Scrapers)
- 多源数据对齐与去重
- 涉及复权因子、财务口径计算

### 核心禁令 (No-Go List)
- **脏数据**: 严禁在未处理 `NaN`、`None` 或 0 股价等异常值的情况下直接输出计算结果。
- **口径对齐**: 严禁在同一表中混合不同复权口径的数据。默认必须使用“前复权”并显式标注。
- **幂等性**: 采集任务必须支持重跑且不产生重复数据。
- **映射验证 (Matrix Check)**: 严禁在未输出“首条记录 API vs DB 对比矩阵”的情况下宣称数据接入成功。
- **灰度同步 (Grey-scale)**: 严禁在未通过“10-50 条记录灰度 QC”的情况下启动全量（>1000 条）历史同步。
- **核心字段零容忍**: 严禁在核心事实字段（如 `total_assets`, `net_profit`, `eps`）存在异常 NULL 率时跳过人工复核。

---

## 7. [Performance Tuner] — 性能与资源专家

### 触发场景
- 处理大规模数据查询 (超过 10w 行)
- 使用 Pandas 进行复杂内存计算
- 修改高频调用的 API 逻辑

### 核心禁令 (No-Go List)
- **内存红线**: 严禁一次性加载超过 10,000 行数据到内存。必须使用流式读取或分段处理。
- **SQL 索引**: 严禁在未经过 `EXPLAIN` 验证索引命中的情况下提交涉及多表关联的查询。
- **异步安全**: 严禁在异步上下文中调用阻塞性库（如 `requests`, `time.sleep`）。

---

## 8. [QA/Test Engineer] — 自动化测试专家

### 触发场景
- 编写测试用例 (`tests/`)
- 提交功能模块交付
- 编写集成测试逻辑

### 核心禁令 (No-Go List)
- **真实性**: 严禁仅使用 Mock 完成测试。必须包含至少一个验证真实数据链通性的集成测试。
- **边界覆盖**: 测试用例必须覆盖“开/闭/停牌”及“网络超时”等异常状态。
- **回归**: 严禁在修改代码后不运行受影响模块的既有测试脚本。

---

## 9. [Gateway Guardian] — 网关与安全卫士 (仅限 WXCH Gateway)

### 触发场景
- 修改 `wxch-gateway` 的 API 路由与控制器
- 处理用户身份校验（OpenID / Auth）
- 涉及 API 报错处理逻辑

### 核心禁令 (No-Go List)
- **身份穿透**: 严禁在未校验 `X-WX-OPENID` 的情况下返回用户私有数据（如自选股）。
- **信息泄漏**: 严禁在 API 异常返回中包含 SQL 语句、数据库堆栈或内部 IP 地址。必须返回模糊的错误信息。
- **移动端负荷**: 严禁单次接口返回超过 500 行的原始记录。必须在服务端完成分页或数据聚合。
- **微信契约**: 严禁修改与小程序端约定的 JSON 结构，除非已同步更新小程序侧代码。

---

## 10. [Security & Code Integrity Auditor] — 安全与代码合规审计师

### 触发场景
- 核心算法重构（如熔断、权重计算）
- 涉及敏感凭据、数据库连接池管理的变更
- 跨微服务通讯逻辑修改
- 提交生产级交付物前

### 核心禁令 (No-Go List)
- **硬编码**: 严禁在代码、注释或日志中出现任何 API Key、密码或内部 IP 地址。
- **资源泄露**: 严禁在没有 `finally` 块或 `async with` 的情况下操作全局资源（Connection Pool/HTTP Client）。
- **根目录污染**: 严禁违反 `AGENTS.md` 规定在根目录创建临时测试文件。
- **静默失败**: 严禁使用 `except: pass` 捕获异常而不记录包含 `request_id` 的结构化日志。

---

## 11. 角色激活机制 (Integration)

### 实施计划中的声明
在 `implementation_plan.md` 的“架构溯源与风险认证”章节中，Agent 必须显式列出本次任务激活的角色：
> **激活角色**: [Requirement Architect], [Backend Engineer], [DB Auditor]

### 验收流程中的调用
在 `walkthrough.md` 中，Agent 应以激活角色的口吻进行自我审查：
- "[Requirement Architect] 已确认 AC 验收标准已 100% 覆盖且逻辑符合规范。"
- "[Backend Engineer] 已确认异步并发安全，所有 IO 均有超时控制且无阻塞调用。"
- "[DB Auditor] 已确认所有 SQL 均包含 `is_deleted = 0` 且字段单位正确。"
- "[Data Quality Steward] 已确认对 Tushare 返回的空值进行了 Fallback 处理。"
- "[Security Auditor] 已确认无敏感凭据泄露，全局连接池已正确管理并释放。"
- "[Performance Tuner] 已通过分页查询将内存占用控制在 128MB 以下。"
- "[QA/Test Engineer] 已通过模拟故障注入完成端到端集成测试，覆盖了 Fail-over 边界。"
- "[Workflow Guard] 已确认真源证据已嵌入附件。"
