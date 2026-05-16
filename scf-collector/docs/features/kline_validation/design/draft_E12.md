# E12: stock_kline_daily 历史数据校验与自动修复体系

## 背景

当前 A 股日线数据采集已具备基础能力，但缺乏系统性的事后质量审计与自动化修复机制。随着 `adj_factor` 内嵌方案的实施，数据的一致性要求从“单表完整”提升到了“跨表/跨源一致”。本 Epic 旨在构建一套能够自动发现空洞、自动对账因子、并自动触发修复的数据管线。

> **评审批注**: 针对日线数据全量巡检的高开销问题，方案调整为「一次基准校验 + 每周增量校验」模式，并根据算力需求实现环境隔离（Docker/SCF）。

## 核心规则：三源对账过滤与对齐逻辑

为了消除不同数据源之间的系统性差异，巡检脚本必须严格遵守以下过滤逻辑：

### 1. 不复权口径对齐 (Raw Data Alignment)
*   **强制约束**：所有比对（本地、Tushare、AkShare）必须强制使用 **“不复权” (Unadjusted/Raw)** 价格。
*   **理由**：不复权 OHLC 是交易所的物理真值，不含任何算法漂移。AkShare 调用必须指定 `adjust=""`。

### 2. 停牌日处理 (Suspension Logic)
*   **对齐基准**：以 `meta_trading_calendar` 为主索引。
*   **过滤规则**：若本地缺失某日记录，但经核实该股当天处于“停牌”状态（Tushare 无记录且 AkShare 成交量为 0），则：
    *   **判定**：视为“合规缺失”，不记录为 Hole。
    *   **例外**：若本地有记录但成交量 > 0（数据污染），则记录为 `redundant_error`。

### 3. 特殊股息与计算偏差 (Special Dividend & Drift)
*   **除权日对冲**：在 `stock_adjust_factor` 校验中，若发现因子差异，优先检查是否为“特殊股息”发放日。
*   **容错处理**：对于不影响价格序列连续性的极小因子差异（< 0.0001），记录为 `Precision_Drift` 而非 `Error`。

## 风险与避坑提示

| 风险 | 表现 | 应对 |
|---|---|---|
| **API 限流** | 自动修复任务触发过快导致 Tushare 封禁 | 修复队列实施令牌桶限流（1 QPS） |
| **修复循环** | 脏数据导致修复失败，系统陷入死循环重采 | 任务设置 max_retries=3，失败转人工审计 |
| **基准校验对数据库压力** | 基准校验涉及 2000 万行扫描，可能产生慢查询 | 基准校验在低峰期于腾讯云 Docker 环境执行，采用 Chunking 分批处理 |

## 里程碑

| 里程碑 | 计划日期 | 交付物 |
|---|---|---|
| **M1** | 2026-05-20 | 基准巡检脚本就绪，输出全市场空洞报告 |
| **M2** | 2026-05-25 | 自动补数任务队列上线，实现“发现即补录” |
| **M3** | 2026-06-01 | 因子一致性对账覆盖率 > 99%，系统进入自愈状态 |

---

## E12: stock_kline_daily 历史数据校验与自动修复体系

### E12-S1: [L2] 分层数据完整性与准确性全量巡检 (Pixel-Level Integrity & Accuracy Checker)

**作为** Data Integrity Steward，**我希望** 建立一套覆盖全量历史数据的“像素级”对账机制，**以便** 通过 Tushare 与 AkShare 的交叉校验，彻底消除 `stock_kline_daily` 与 `stock_adjust_factor` 中的脏数据。

#### 任务

- E12-S1-T1 开发具备“三源仲裁”功能的巡检脚本（Local vs Tushare vs AkShare）
- E12-S1-T2 创建 `meta_task_queue` 任务对账表，建立巡检到修复的闭环链路
- E12-S1-T3 执行全量像素级对账 (Full Mode: 1991年-至今)，识别空洞与数值错误
- E12-S1-T4 建立因子表 `stock_adjust_factor` 的专项完整性巡检
- E12-S1-T5 在 SCF 中部署每周增量巡检任务 (Delta Mode)

#### 验收标准（AC）

- **AC1: 增量巡检准确性**
  - **Given** 基准校验已完成，`meta_config` 记录最后水位线
  - **When** 执行 Delta 模式巡检
  - **Then** 脚本仅对比水位线至今的交易日缺失情况，自动跳过已知停牌日，扫描性能满足 SCF 900s 限制

- **AC2: 三源对账仲裁可靠性**
  - **Given** 某记录本地价为 10.01，Tushare 为 10.00，AkShare 为 10.00
  - **When** 运行 Full 模式审计（强制不复权口齐）
  - **Then** 脚本必须自动判定 Tushare 与 AkShare 达成共识，将本地记录标记为 `need_repair` 并建议修复值为 10.00

- **AC3: 审计报告交付**
  - **Given** 全量巡检完成
  - **When** 查看 `REPORT.html`
  - **Then** 必须包含历史错误分布热力图（Heatmap）及前 100 条三源差异明细，且支持在移动端直观查看

---

### E12-S2: [L3] 因子对账与计算一致性审计 (Factor Auditor)

**作为** DB Auditor，**我希望** 对回填后的内嵌因子计算出的复权价与官方 API 进行比对，**以便** 确保回填逻辑无偏差。

#### 任务

- E12-S2-T1 实现随机抽样对账逻辑（每次随机 1000 个采样点）
- E12-S2-T2 对比公式：`abs(close * adj_factor / latest_factor - tushare_qfq_close) < 0.01`
- E12-S2-T3 输出误差超过 0.1% 的详细审计报告至 `REPORT.html`

#### 验收标准（AC）

- **AC1: 计算一致性**
  - **Given** 抽取任意 1000 个采样点
  - **When** 执行对账审计
  - **Then** 除去由于四舍五入导致的极小误差外，异常点（误差 > 0.5%）的比例必须低于 0.1%

- **AC2: 因子跳变捕获**
  - **Given** 某股票发生除权，因子已更新但 K 线未回填最新值
  - **When** 审计脚本运行
  - **Then** 该股必须出现在审计异常清单中，并标记为 `reason='factor_mismatch'`

---

### E12-S3: [E6] 任务化自动补数逻辑 (Auto-Recovery Pipeline)

**作为** Cloud Collector，**我希望** 自动消费任务队列中的缺失/错误记录并重采数据，**以便** 系统实现全自动自愈。

#### 任务

- E12-S3-T1 开发 `functions/auto_repair/index.py` 云函数
- E12-S3-T2 对接 `meta_task_queue`，支持多源补偿（先 Tushare，失败后转 AkShare）
- E12-S3-T3 实现修复成功后的审计日志留痕（`meta_repair_history`）

#### 验收标准（AC）

- **AC1: 闭环修复验证**
  - **Given** `meta_task_queue` 存在缺失数据任务
  - **When** 启动自动修复云函数
  - **Then** 缺失的 K 线行被正确插入 `stock_kline_daily`，且该任务状态更新为 `done`

- **AC2: 幂等与安全**
  - **Given** 修复任务重复执行
  - **When** 多次触发同一个修复 ID
  - **Then** 数据库不会产生重复行（ON DUPLICATE KEY 保证），且历史记录中仅记录第一次修复成功的标识

---

## 变更记录

| 日期 | 版本 | 变更说明 | 作者 |
|---|---|---|---|
| 2026-05-15 | v1.0 | 评审通过，发布正式版本 | Antigravity |
| 2026-05-15 | v0.2 | 评审修正：引入分层巡检模式 (Full/Delta) 及 Docker/SCF 环境隔离 | Antigravity |
| 2026-05-15 | v0.1 | 初稿生成 | Antigravity |
