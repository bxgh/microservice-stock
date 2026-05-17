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
  - 全局架构类设计存放于根目录 `docs/` 下的 `domains/{domain_name}/` 目录。
  - **微服务专属设计与实施文档** (含 Epic/Story/Plan/Task) **必须** 物理存放于该服务目录下的 `docs/features/{feature_name}/` 文件夹中。
  - `{feature_name}/` 内部强制划分为 `design/` (设计稿), `reviews/` (评审记录), `implementation_logs/` (实施日志) 三个子目录。
- **实施日志路径**: 必须按照设计文档同目录下的 `implementation_logs/E{N}/S{M}/` 文件夹进行物理存证。

> **文档归口原则**: 严禁在根目录 `docs/` 随意堆放微服务专属文档。针对 `scf-collector`, `tushare-api` 等微服务的所有 Epic/Story 设计及实施日志，**必须** 物理存放于该微服务 `docs/features/{feature_name}/` 文件夹下的对应子目录中。

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
- [ ] **结构化设计**: 必须使用 `epic-story-doc` 生成 `draft_E{N}.{md,json}` 并存放于微服务 `docs/` 下。
- [ ] **状态对齐**: 若本 Epic 已有前置 Story 完结，必须前置读取并完全对齐 `state_E{N}.json` 状态文件以恢复环境上下文（参考 5.7.8 节）。
- [ ] **依赖认证**: 查实 `TABLES_INDEX.md` 及环境连通性。
- [ ] **角色激活**: 显式声明激活的角色（参考 `docs/architecture/agent-skill-rules/ROLES.md`）。

### 5.2 实施过程规范
1. **禁止无文档开发 (Docs-First)**: 严禁未经本地 `implementation_plan.md` 和 `task.md` 存证直接编写代码。
2. **Task ID 进 Commit**: 每个 Task 对应一个 Commit，前缀 `[E1-S1-T1]`。
3. **验收前必跑 AC**: 所有验收标准 (AC) 必须转为可执行测试。
4. **采集清单同步**: 每一项云函数采集开发完成后，必须同步更新该微服务下的 `docs/done-list-tables.md`，记录已落地的表名、采集频率及关键 AC 达成情况。
5. **HTML 文档导航 (Portal)**: 
   - 所有的需求设计、技术文档、完成报告必须额外产出 **HTML 格式** 副本。
   - 完成任何 HTML 交付物后，必须运行 `python scripts/update_docs_portal.py` 更新全局与局部门户。
   - 全局门户: [docs/index.html](file:///e:/gitee/microservice-stock/docs/index.html)；局部门户: `{service}/index.html`。

### 5.3 验证“真源”准则
- **物理查验**: 必须通过 `docker exec` 或 SQL 直连数据库确认真实记录，严禁盲目信任 API 返回值。
- **存证要求**: `walkthrough.md` 必须包含真实的 SQL 结果块或日志片段。
- **交付物闭环**: 每一项 Story (S) 开发完成后，必须在对应的 `implementation_logs/E{N}/S{M}/` 目录下生成 `REPORT.html` (技术报告/HTML版) 及 `API.md` (如有接口变更)。**同时，必须在 `implementation_logs/E{N}/` 目录下增量更新或新建 `state_E{N}.json` 状态存证文件**，以机器可读（AI-Native）的结构化形式记录当前物理产出与下游交接备注。

### 5.4 数据质量闭环 (QC Feedback Loop)

1. **映射双检**: 所有 `ods_` 层接入必须输出“字段对齐矩阵”脚本及结果。
2. **灰度先行**: 历史同步必须遵循 `10只股票样本 -> 校验 -> 全量回填` 的三段式流程。
3. **空值红线**: 核心字段（Fact）在回填结束后必须执行 `COUNT(*) WHERE IS NULL` 审计。

### 5.5 结构化评审循环 (Epic Audit Loop)

1. **设计生成**: 使用 `epic-story-doc` 生成 `draft_E{N}.json`。
2. **评审开启**: 运行 `python .agents/skills/epic-story-doc/inject.py {path_to_json}` 生成评审 HTML。
3. **反馈闭环**: 
   - 用户在评审页标注修改意见并导出 `review_result.json`。
   - Agent 读取该 JSON 并调用 `epic-story-doc` 的重生成逻辑更新设计。
4. **通过准则**: 只有在评审页所有 Story 状态为 `ok` 且 `draft_E{N}.md` 同步更新后，方可进入 Story 实施。

### 5.6 SCF 兼容性强约束 (Binary Integrity)

1.  **禁止 Windows 原生打包**: 严禁在 Windows 环境下直接通过 `pip install -t .` 打包依赖并上传。
2.  **强制平台审计**: 所有上传至 SCF 的依赖包必须通过 `scripts/scf_build_tool.py` 进行构建。
3.  **零容忍红线**: 构建过程中如果审计发现任何 `.pyd` 文件，必须立即停止构建并报错，严禁跳过审计上传。
4.  **环境一致性**: 强制指定 `--platform manylinux2014_x86_64` 和 `--only-binary=:all:`。

### 5.7 敏捷迭代与技术沉淀机制 (Agile Iteration & Tech Deposition)

1. **临时/紧急需求绿色通道 (Ad-hoc Task Bypass)**:
   - **适用场景**: 独立测试/验证脚本（如 `scratch/` 下的单次运行脚本）、少于 3 行逻辑的紧急线上 Bug 修复、纯配置调整、本地一次性数据回填。
   - **豁免条件**: 豁免繁琐的 `draft_E{N}.md` 设计审查与正式的 `implementation_plan.md` / `task.md`。
   - **极简审计门禁**:
     - 必须在相关服务目录的 `scratch/README.md` 或脚本头部以注释形式，用 1-2 句话说明“目的”与“影响范围”。
     - 提交 Commit 时，前缀强制使用 `[AD-HOC]`，严禁使用常规 Epic 编号。
     - 跨模块临时脚本必须收拢在根目录的 `scratch/history/` 文件夹下。
2. **避坑与技术秘籍记录 (Story Pitfall & Tech Tips)**:
   - **规范要求**: 在 Story 交付物中，强制增设对于开发中遇到的诡异 Bug、性能瓶颈、网络/权限受阻等踩坑记录的沉淀。
   - **记录要素**: 必须包含 **踩坑记录 (The Pitfall)**、**方案对比 (Options Explored)**、**择优决策 (Optimal Choice)**、**复用技巧 (Reusable Tips)**。
3. **知识与避坑文档双轨命名规范 (Knowledge Suffix Naming Standard)**:
   - **双轨专属后缀**: 为了便于全局搜索与工具链自动检索，所有具有知识意义的总结、技术技巧、排障避坑文档，其文件名必须强制使用结构化的双后缀：
     - **排障避坑/方案决策**: 使用 **`*.pitfall.md`**（对应的 HTML 副本为 `*.pitfall.html`）。*示例*: `tushare_ip_block.pitfall.md`
     - **技术秘籍/最佳实践**: 使用 **`*.kb.md`**（对应的 HTML 副本为 `*.kb.html`）。*示例*: `scf_memory_tuning.kb.md`
     - **终结/阶段性总结**: 使用 **`*.summary.md`**（对应的 HTML 副本为 `*.summary.html`）。*示例*: `e12_kline_healing.summary.md`
4. **AI 友好索引与自动门户集成 (AI-Native Indexing & Portal Integration)**:
   - **双规自动集成**:
     - 自动化门户更新脚本 `scripts/update_docs_portal.py` 将自动扫描微服务目录下所有的 `*.kb.html`、`*.pitfall.html` 和 `*.summary.html` 文件。
     - **人类视角**: 自动提取其首行 `# 标题`，在全局门户 `docs/index.html` 中生成 **“知识与避坑技术库”** 板块。
     - **AI 视角**: 同步在 `docs/` 根目录下生成轻量级、高密度的机器学习友好索引 `docs_portal_index.json`。AI Agent 启动时应优先读取该 JSON 获得系统的“知识地图”，从而以最低 Token 消耗精确定位并秒载目标避坑资产。
5. **规则传导与注入规约 (Rule Infiltration to Active Rules)**:
   - **动态传导**: 当 `*.pitfall.md` 或 `*.kb.md` 沉淀出**系统级强约束**（如 API 流控重试、异步锁死区等）时，必须同步以简练的 1 行陈述句，增补进 `.agent/rules/python-coding-standards.md` 或 `AGENTS.md` 的 `6. 反模式清单` 中，实现“热注入”约束红线。
6. **Story/Epic 迭代演进机制 (Iteration Governance)**:
   - **规范要求**: 当同一个 Epic 或 Story 在后续系统演进中产生二次迭代或重构时，**严禁**直接覆盖原始实施日志以防历史追溯丢失。
   - **实施规范**:
     - 在对应的 `implementation_logs/E{N}/S{M}/` 下新建 `iterations/v2/`（或以日期命名如 `v20260517/`）子文件夹。
     - 撰写 `ITERATION_NOTE.md`（及 HTML），阐明：
       1. **迭代触发动因 (Trigger)**：为什么要改？
       2. **影响面评估 (Impact Map)**：改动了哪些存量表、核心类或接口？
       3. **回归验证清单 (Regression AC)**：包含哪些回归测试用例，如何确保不影响存量老功能。
     - Commit 提交前缀格式变更为 `[E{N}-S{M}-V2]` 或 `[E{N}-S{M}-ITER]`.
7. **知识时效性与“过时信息”治理 (Knowledge Freshness & Deprecation Protocol)**:
   - **唯一真源原则**: 无论是历史文档还是避坑指南，其描述若与现行代码实现、现行 MySQL/ClickHouse 物理 DDL 冲突，**必须以现行代码和物理 Schema 为唯一真源**。开发人员与 AI 代理在采用任何历史经验前，必须前置执行物理状态核验。
   - **最新版优先原则**: 如果某个 Story 存在迭代目录（如 `iterations/v2/`），则 `v2` 中的设计与规范描述自动覆盖 `v1` 中的同名描述。
   - **过期强打标机制**: 一旦某历史文档（`*.pitfall.md` / `*.kb.md`）中的解决方案被新系统设计彻底推翻、重构或废弃，**必须**在该历史文档顶部以 GitHub Alerts 语法标记 `> [!WARNING] 本文档描述的方案/Bug 已在 E{X}-S{Y} 中被重构/废弃，最新方案参考 [新文档路径](file:///...)`。
   - **自动过滤机制**: 自动化门户更新脚本 `scripts/update_docs_portal.py` 在扫描发现包含 `> [!WARNING] *废弃*` 或 `*过期*` 标识的文档时，必须在 AI 友好索引 `docs_portal_index.json` 中自动将其标记为 `deprecated: true` 并排除在活跃知识库列表之外，防止 AI Agent 误吸入过时信息。

8. **AI-to-AI 跨会话增量状态交接协议 (AI-to-AI Session Handoff Specification)**:
   - **必要性**: 同一个 Epic 下的不同 Story 极可能跨越不同的对话会话（Chat Session）甚至由不同的 AI Agent 实例承接开发。由于 AI 本身无法继承历史会话的运行内存，依靠纯人类文档（Markdown）交接容易造成“上下文稀释”和状态盲区。
   - **规范要求**: 在微服务目录 `docs/features/{feature_name}/implementation_logs/E{N}/` 下，必须建立且仅建立一个累加增量更新的状态文件 **`state_E{N}.json`**。
   - **交接动作**: 
     - **Story 实施前**: 必须将 `state_E{N}.json` 作为“唯一环境真源”读取并同步至系统内存，完成状态对齐。
     - **Story 完结时**: 必须以结构化 JSON 对当前交付进行存证，增量写入已交付的物理列、新增接口以及后续 Story 实施的强置前置条件与明确交接备注（`handoff_notes`）。
   - **数据结构定义**: 必须严格包含 `epic_id`、`last_updated`、`current_stage`、`completed_stories` (包含已交付物理资产及 downstream notes)、`active_system_state` 以及 `next_story_tasks` 等核心字段。

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
| 2026-05-12 | v1.7 | **交付标准化**: 强化 5.2 节，要求云函数开发完成后必须同步更新 `done-list-tables.md`。 |
| 2026-05-15 | v1.8 | 文档门户化: 引入 HTML 文档导航系统，要求所有报告产出 HTML 版并同步至 Portal。 |
| 2026-05-15 | v1.9 | **SOP 闭环化**: 强制要求 Epic-Story 设计评审循环，实现全局+局部双级门户自动化。 |
| 2026-05-17 | v2.0 | **敏捷与沉淀**: 优化临时需求免审通道，确立知识文档双轨后缀(*.kb.md/*.pitfall.md)，引入 Epic 终结总结、迭代演进目录及 AI-Native 自动索引规范。 |
| 2026-05-17 | v2.1 | **交接标准化**: 引入 AI-to-AI 跨会话增量状态交接规范，在 implementation_logs/E{N}/ 下引入 state_E{N}.json 状态文件实现 Story 间机器级无缝衔接。 |

