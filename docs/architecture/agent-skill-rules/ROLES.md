# 虚拟 Agent 角色定义 (Virtual Role-based Rules)

> 为了防止 Agent 在长序列对话中遗忘复杂的工程标准，我们将约束拆分为多个虚拟角色。Agent 在执行特定任务时应通过"思维链"显式激活对应角色。
>
> **版本**: v2.0 | **最后更新**: 2026-05-14

---

## 0. [Universal Constraints] — 全局通用禁令

> 以下约束对所有角色无条件生效，不在各角色中重复声明。

- **硬编码零容忍**: 严禁在任何代码、注释、日志、配置文件中出现 API Key、数据库密码或内部 IP。必须统一通过 `os.getenv` 读取，且对应变量必须在 `.env.example` 中有占位文档。
- **异步阻塞禁令**: 严禁在异步上下文中调用 `requests`、`time.sleep` 或任何同步阻塞 IO 库。必须使用 `httpx` / `aiohttp` + `asyncio.sleep`。
- **资源闭环**: 严禁在任何外部 IO 操作（DB / HTTP / 文件）中缺少 `try...finally` 或 `async with` 资源回收逻辑。
- **静默失败禁令**: 严禁使用裸 `except: pass`。异常必须记录包含 `request_id` 的结构化日志后再决定是否 re-raise。
- **错误脱敏**: 严禁在任何对外接口（HTTP 响应 / 日志聚合平台）中透传原始 Traceback、SQL 语句或内部 IP。

---

## 1. 角色激活矩阵 (Activation Matrix)

> Agent 开始任务前必须查表，确定本次需激活的全部角色，并在思维链中声明。

| 任务类型 | 必激活角色 |
|---|---|
| 编写 / 修改数据采集脚本 | DB Auditor, Data Quality Steward, Backend Engineer, Performance Tuner |
| 编写业务逻辑 / API 路由 | Backend Engineer, Security & Code Integrity Auditor |
| 修改 WXCH Gateway 路由或身份校验 | Gateway Guardian, Security & Code Integrity Auditor, Backend Engineer |
| 编写 SQL / DAO 层 / 数据库迁移 | DB Auditor, Performance Tuner |
| 接收新 Epic / Story，产出实施计划 | Requirement Architect, Workflow Guard |
| 提交功能交付 / 编写 walkthrough | Workflow Guard, QA/Test Engineer, Security & Code Integrity Auditor |
| 部署配置 / 环境变量 / Docker | Infra Specialist, Security & Code Integrity Auditor |
| 核心算法重构 | Performance Tuner, Security & Code Integrity Auditor, Backend Engineer |
| 编写测试用例 | QA/Test Engineer |

---

## 2. [DB Auditor] — 数据库审计专家

### 触发场景
- 涉及 SQL 编写（CRUD）
- 修改 DAO 层代码
- 编写数据库迁移脚本 (Migrations)

### 核心禁令 (No-Go List)

- **命名**: 严禁使用 `stock_code` / `dt` / `pct`。必须使用 `ts_code` / `trade_date` / `pct_chg`。

- **软删除**: 任何 SELECT 查询必须包含 `is_deleted = 0`。
  > ✅ 例外：老表（如 `stock_basic_info`）必须先执行 `DESCRIBE <table_name>` 物理确认字段存在，再决定是否添加该过滤条件。未确认前默认不加。

- **单位**: `amount` 强制为"元"，`pct_chg` 强制为小数形式（如 `0.0123`，而非 `1.23`）。

- **MySQL 5.7 兼容性**:
  - 严禁使用窗口函数 (`OVER`) 和 CTE (`WITH`)。
  - 执行 `ON DUPLICATE KEY UPDATE` 时，必须显式更新 `updated_at = CURRENT_TIMESTAMP`，否则字段在值未变时不会自动触发。
  > ✅ 如需行号/排名逻辑，改用子查询 + 用户变量模拟。

- **DDL 三件套**: 新表必须包含 `created_at`、`updated_at`、`is_deleted` 字段及 `idx_updated_at` 索引。

- **ClickHouse 路由规则**（与 [Infra Specialist] 协同）：
  - 读操作行数预估 > 10 万行 → 必须路由至 ClickHouse；
  - 事务操作 / 实时写入 / `ON DUPLICATE KEY UPDATE` → 必须使用 MySQL；
  - 严禁跨引擎 JOIN（即同一查询中混用 MySQL 表和 ClickHouse 表）；
  - ClickHouse 写入必须使用批量 INSERT（单次 ≥ 100 行），严禁逐行写入。

---

## 3. [Backend Engineer] — 后端工程专家

### 触发场景
- 编写业务逻辑代码 (Business Logic)
- 定义 Pydantic 模型、FastAPI 路由或中间件
- 封装通用工具类 (Utils) 或装饰器
- 处理异步并发逻辑 (Async/Await)

### 核心禁令 (No-Go List)

- **并发安全**: 严禁在操作共享可变状态（如内存缓存）时忽略 `asyncio.Lock()`。

- **SCF Client 复用**: 在 SCF 环境下，严禁在每次方法调用中重复初始化 API Client（如 `pro_api`），必须在构造函数中持久化复用。
  > ✅ 在 `__init__` 中初始化一次并赋值给 `self._client`，后续调用复用该实例。

- **模型严谨性**: 严禁在 Pydantic 模型中使用 `Any` 或未定义验证规则的字段；严禁绕过模型校验直接处理原始 `dict`。

---

## 4. [Workflow Guard] — 流程质量哨兵

### 触发场景
- 开始新任务（Readiness Check）
- 提交代码或更新实施进度
- 编写 `walkthrough.md`

### 任务类型区分

| 任务类型 | 准入要求 |
|---|---|
| `Feature Task` | 必须通过 Readiness Check；必须有 `implementation_plan.md` + `task.md` 存证 |
| `Hotfix / Debug` | 可豁免文档先行；必须在 commit message 中注明 `[HOTFIX]` 并在 `walkthrough.md` 中补充事后说明 |

### 核心禁令 (No-Go List)

- **准入**: 严禁在未通过 Readiness Check（需求解析、依赖认证、TBD 销账）的情况下开始 Feature 开发。

- **Git 规范**: 严禁使用非标准格式的 commit。必须包含 `[Task ID]` 且遵循 Conventional Commits。
  > ✅ 格式示例：`feat(scraper): [T-42] add daily limit detection for SZSE stocks`

- **证据链 (QA Exit)**: 严禁编写仅有文字描述的 `walkthrough.md`。必须包含"物理真源证据"（SQL 结果截图 / 日志片段），且证据必须 100% 覆盖设计文档中的 AC。

- **质量审计**: 严禁在静态扫描（`data_validator.py`）未通过的情况下完成任务。

- **安全性**: 严禁提交任何未被 `.gitignore` 排除且含有本地敏感配置的 `scratch/` 脚本。

- **粒度**: 严禁跨 Task 开发。每个 Task 对应一个 Commit，严禁 squash 多 Task。

- **归档**: 严禁将实施日志保存到非指定目录。

---

## 5. [Requirement Architect] — 需求与方案架构师

### 触发场景
- 接收到新的 Epic / Story
- 编写 `implementation_plan.md`
- 定义或调整验收标准 (AC)

### 核心禁令 (No-Go List)

- **AC 可测试性**: 严禁产出不具备可测试性的 AC。每个 AC 必须对应明确的 Given-When-Then 逻辑。
  > ✅ 示例：`Given 当日为非交易日, When 调用采集接口, Then 接口返回空结果并写入 WARN 日志，不抛出异常`

- **禁止硬编码调度**: 严禁在 `jobs.py` 中使用 `@scheduler.scheduled_job('cron', ...)` 装饰器。所有盘后任务必须接入 `WorkflowManager` 事件链或保底扫描机制。

- **一致性**: 严禁设计与 `PROJECT_OVERVIEW.md` 或 `TABLES_INDEX.md` 冲突的业务口径（如单位、字段名）。

- **防御性设计**: 严禁忽略外部依赖（API/DB）失效时的补偿或降级逻辑。
  > ✅ 每个外部依赖必须在 AC 中明确声明降级策略（如：熔断后写入死信队列 / 跳过并告警）。

- **溯源**: 严禁在没有回链设计文档 E/S 编号的情况下创建 Task。

---

## 6. [Infra Specialist] — 基建与环境专家

### 触发场景
- 涉及环境部署、网络调用
- 配置 `.env` 或 `docker-compose`
- ClickHouse 与 MySQL 数据路由决策

### 核心禁令 (No-Go List)

- **部署节点**: 本仓所有服务默认必须部署在腾讯云环境（CVM / 容器），严禁部署至内网 Node-41。

- **网络韧性**: 涉及外部 API 调用（Tushare / AkShare）必须实现熔断（Circuit Breaker）与指数退避重试，严禁在无异常处理的情况下直连。

- **架构接力**: 严禁在云端执行耗时超过 5 分钟的大规模计算任务。此类任务必须通过 `task_commands` 指令下发至内网 Node-41 执行。

- **数据流**: Python 结果集输出到 downstream 前必须控制在 10,000 行以内。

- **空值日志**: 严禁在接口返回空结果（如非交易日请求）时静默退出，必须写入明确的 WARN 日志以区分"系统故障"与"正常空态"。

- **物理查验**: 严禁盲目信任 API 返回值，必须通过容器日志或数据库物理记录验证执行结果。

- **WXCH 适配**: 在微信云托管环境部署时，严禁硬编码 DB 连接 IP，必须使用云托管控制台注入的环境变量及内网域名。

- **ClickHouse 路由决策**（与 [DB Auditor] 协同）:

  | 场景 | 路由目标 |
  |---|---|
  | 预估读取 > 10 万行 / 聚合分析 / 历史回溯 | ClickHouse |
  | 事务写入 / 实时更新 / `UPSERT` | MySQL |
  | 跨引擎 JOIN | **禁止**，必须在应用层分两次查询后合并 |
  | ClickHouse 批量写入 | 单次 ≥ 100 行，严禁逐行 INSERT |

---

## 7. [Data Quality Steward] — 数据治理专家

### 触发场景
- 编写或修改数据采集脚本 (Scrapers)
- 多源数据对齐与去重
- 涉及复权因子、财务口径计算

### 核心禁令 (No-Go List)

- **脏数据**: 严禁在未处理 `NaN`、`None` 或 0 股价等异常值的情况下直接输出计算结果。
  > ✅ 必须在采集管道入口处统一执行异常值过滤，并记录过滤行数到监控指标。

- **口径对齐**: 严禁在同一表中混合不同复权口径的数据。默认必须使用"前复权"并在字段注释中显式标注。

- **幂等性**: 采集任务必须支持重跑且不产生重复数据。
  > ✅ 使用 `ON DUPLICATE KEY UPDATE` 或先查后写模式保证幂等。

- **映射验证 (Matrix Check)**: 严禁在未输出"首条记录 API vs DB 对比矩阵"的情况下宣称数据接入成功。

- **灰度同步 (Grey-scale)**: 严禁在未通过"10–50 条记录灰度 QC"的情况下启动全量（> 1000 条）历史同步。

- **核心字段零容忍**: 严禁在核心事实字段（如 `total_assets`、`net_profit`、`eps`）存在异常 NULL 率时跳过人工复核。

---

## 8. [Performance Tuner] — 性能与资源专家

### 触发场景
- 处理大规模数据查询（超过 10 万行）
- 使用 Pandas 进行复杂内存计算
- 修改高频调用的 API 逻辑

### 核心禁令 (No-Go List)

- **内存红线**: 严禁一次性加载超过 10,000 行数据到内存。必须使用流式读取（`yield`）或分段处理（按 `trade_date` 分批）。

- **SQL 索引**: 严禁在未经 `EXPLAIN` 验证索引命中的情况下提交涉及多表关联的查询。
  > ✅ `EXPLAIN` 输出的 `type` 列不得出现 `ALL`（全表扫描），否则必须补充索引或重写查询。

---

## 9. [QA/Test Engineer] — 自动化测试专家

### 触发场景
- 编写测试用例 (`tests/`)
- 提交功能模块交付
- 编写集成测试逻辑

### 核心禁令 (No-Go List)

- **真实性**: 严禁仅使用 Mock 完成测试。每个功能模块必须包含至少一个集成测试，该测试须满足：
  - 连接 **Staging 环境**（或本地 Docker 起的真实数据库），不得使用内存数据库替代；
  - 验证从接口入参到数据库落库的完整链路；
  - 在 `walkthrough.md` 中附上该测试的执行日志截图。

- **边界覆盖**: 测试用例必须覆盖以下异常状态：
  - 股票处于开盘 / 停牌 / 退市状态；
  - 外部 API（Tushare / AkShare）网络超时；
  - 非交易日请求返回空结果。

- **回归**: 严禁在修改代码后不运行受影响模块的既有测试脚本。
  > ✅ 提交前必须在本地执行 `pytest tests/<affected_module>/ -v` 并确认全部 PASS。

---

## 10. [Gateway Guardian] — 网关与安全卫士 (仅限 WXCH Gateway)

### 触发场景
- 修改 `wxch-gateway` 的 API 路由与控制器
- 处理用户身份校验（OpenID / Auth）
- 涉及 API 报错处理逻辑

### 核心禁令 (No-Go List)

- **身份穿透**: 严禁在未校验 `X-WX-OPENID` 的情况下返回用户私有数据（如自选股）。
  > ✅ 所有涉及用户私有数据的路由必须在中间件层完成 OpenID 鉴权，不得在 Handler 层补打补丁。

- **移动端负荷**: 严禁单次接口返回超过 500 行的原始记录。必须在服务端完成分页或数据聚合后再返回。

- **微信契约**: 严禁修改与小程序端约定的 JSON 结构，除非已同步更新小程序侧代码并在同一 PR 中提交。

> ℹ️ **通用安全约束**（信息泄漏防护、硬编码禁令）由 [Universal Constraints] 和 [Security & Code Integrity Auditor] 统一管辖，本角色不重复声明。

---

## 11. [Security & Code Integrity Auditor] — 安全与代码合规审计师

### 触发场景
- 核心算法重构（如熔断、权重计算）
- 涉及敏感凭据、数据库连接池管理的变更
- 跨微服务通讯逻辑修改
- 提交生产级交付物前

### 核心禁令 (No-Go List)

- **连接池泄露**: 严禁在没有 `finally` 块或 `async with` 的情况下操作全局资源（Connection Pool / HTTP Client）。
  > ✅ 所有 DB 连接必须通过上下文管理器获取，连接池初始化状态必须在服务启动日志中可观测。

- **根目录污染**: 严禁在根目录创建临时测试文件。调试脚本统一放入 `scratch/`，且必须被 `.gitignore` 覆盖。

- **依赖审计**: 新增第三方依赖前必须确认其 License 兼容性，并在 `requirements.txt` 中锁定精确版本号（`==x.y.z`）。

---

## 12. 角色激活机制 (Integration)

### 实施计划中的声明

在 `implementation_plan.md` 的"架构溯源与风险认证"章节，Agent 必须显式列出本次任务激活的角色：

> **激活角色**: [Requirement Architect], [Backend Engineer], [DB Auditor]

### 验收流程中的自审

在 `walkthrough.md` 中，Agent 应以激活角色的口吻逐条自审：

- "[Requirement Architect] 已确认所有 AC 均具备 Given-When-Then 可测试逻辑，覆盖率 100%。"
- "[Backend Engineer] 已确认异步并发安全，所有 IO 均有超时控制且无阻塞调用；SCF Client 在构造函数中单例初始化。"
- "[DB Auditor] 已确认所有 SQL 包含 `is_deleted = 0`（或已通过 DESCRIBE 确认字段缺失的老表豁免），字段单位正确，MySQL 5.7 兼容性已验证。"
- "[Data Quality Steward] 已输出 API vs DB 对比矩阵，已通过灰度 QC，核心字段 NULL 率在阈值内。"
- "[Security & Code Integrity Auditor] 已确认无敏感凭据泄露，连接池通过 `async with` 管理，`scratch/` 已被 `.gitignore` 覆盖。"
- "[Performance Tuner] 已通过 `EXPLAIN` 确认索引命中，内存分段处理峰值在 128 MB 以下。"
- "[QA/Test Engineer] 已在 Staging 环境完成端到端集成测试，覆盖停牌/非交易日/网络超时边界，日志截图已附入 walkthrough。"
- "[Workflow Guard] 已确认物理真源证据嵌入 walkthrough，Task 粒度与 Commit 一一对应，`data_validator.py` 扫描通过。"