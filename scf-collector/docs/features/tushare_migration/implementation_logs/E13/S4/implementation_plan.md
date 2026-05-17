# E13-S4: 财务三表与关键比率迁移 — 实施计划

本实施计划旨在将历史财务报表（利润表、资产负债表、现金流量表）以及关键财务指标数据（毛利率、净利率、ROE、流动比率等）全面、稳健地从旧的 BaoStock/CVM 迁移至 **Tushare Pro** 数据源。该计划由 **[Data Steward]** 角色激活并主导实施。

特别针对用户提出的**“防止跟数据库已有数据重复数据入库”**要求，本计划在物理数据库层和 Python 业务逻辑层实施**双重去重与幂等保障策略**。

---

## 1. 准入审查 (Readiness Check)

在正式启动本 Story (E13-S4) 实施前，各项条件对齐如下：
- [x] **需求解析**: 开发针对 A 股全市场个股的历史财务三表与估值/财务指标的高性能、单线程断点续传同步脚本。清空存量数据，以 Tushare Pro（2000积分）作为唯一真源，实现全量回填与字段高精度对齐。
- [x] **结构化设计**: 设计稿 `draft_E13.md` 已于 `scf-collector/docs/features/tushare_migration/design/` 归档。
- [x] **状态对齐**: 累加增量状态文件 `state_E13.json` 已创建并对齐，记录了 S1-S3 的交付。
- [x] **依赖认证**: 物理表结构已在 `migrations/20260509_create_ods_financial_tables.sql` 中完全就绪，包含尾部三件套及其索引。
- [x] **角色激活**: **[Data Steward]**。

---

## 2. 核心架构设计

本次财务数据迁移具有**数据量大**、**Tushare 限流频次高**（200次/分）的特点。因此，严格采用以下策略：

### 2.1 物理隔离与单线程 Throttling
- **物理运行环境**: 部署于腾讯云生产服务器环境（Tencent Cloud Environment），运行不限时。**禁止在 SCF (Serverless Cloud Function) 内运行该回填任务**。
- **采集粒度**: 采用**个股循环（ts_code）**拉取完整历史的策略，而非按报告期拉取。每次拉取一只股票的所有历史财报。
- **速率控制（Throttling）**: 针对 `balancesheet`/`income`/`cashflow`/`fina_indicator` 接口，**每拉取完一只股票，必须强行 `await asyncio.sleep(1.5)`**。此操作不仅可完全避免 200次/分钟 的流控拦截，也避免对混合 MySQL 数据库产生持续高负载并发写入压力。

### 2.2 字段与口径标准化
- **单位红线**: Tushare 官方财报金额单位为 **元**。数据库存储严格以“元”为精度，禁止任何编造或转换。
- **百分比 -> 小数**: Tushare 的财务指标接口中 `roe` (净资产收益率), `grossprofit_margin` (销售毛利率), `netprofit_margin` (销售净利率), `debt_to_assets` (资产负债率) 均为百分比值（如 15.5 表示 15.5%）。在入库前**必须统一除以 100.0**，转换为 `decimal(10,4)` 的标准小数格式（如 `0.1550`），与 `AGENTS.md` 规范 and `daily_basic` 口径保持一致。
- **合并/单体报表**: 默认仅拉取合并报表（Tushare 接口的 `report_type = '1'`）。
- **披露日对齐**: 严格分离 `ann_date` (公告日) 与 `end_date` (报告期末)，避免未来函数污染。

---

## 3. 防重复入库与幂等设计 (Double-Layer Deduplication)

为了确保数据不重复、不冲突，系统实施以下双重防护体系：

```mermaid
graph TD
    Tushare[Tushare API 返回数据] --> PyFilter[1. Python 业务层过滤: 按 (ts_code, end_date, report_type) 分组, 保留最新公告日数据]
    PyFilter --> MySQLUnique[2. MySQL 物理约束: 触发唯一索引 uk_code_period_type 拦截]
    MySQLUnique --> Upsert[3. ON DUPLICATE KEY UPDATE: 执行高精细度更新, 确保单条记录更新而非新增]
```

### 3.1 第一层：MySQL 物理唯一索引约束 (Database-Level Barrier)
在 `migrations/20260509_create_ods_financial_tables.sql` 中，我们为各表设计了严格的联合唯一索引。这是防止重复数据入库的物理红线：
- **财务三表** (`ods_fin_balancesheet`, `ods_fin_income`, `ods_fin_cashflow`):
  ```sql
  UNIQUE KEY uk_code_period_type (ts_code, end_date, report_type)
  ```
  *(物理保证：同只股票、同报告期、同报表类型的记录在数据库中仅允许存在一行。)*
- **财务指标表** (`ods_fin_indicators`):
  ```sql
  UNIQUE KEY uk_code_period (ts_code, end_date)
  ```
  *(物理保证：同一只股票、同一报告期的财务指标记录仅允许存在一行。)*

### 3.2 第二层：MySQL 幂等插入语法 (`ON DUPLICATE KEY UPDATE`)
所有入库 SQL 坚决不使用盲目的 `INSERT INTO`，而是采用 `INSERT INTO ... ON DUPLICATE KEY UPDATE`：
- **逻辑行为**: 当尝试插入的数据在 `uk_code_period_type` 联合唯一键上与已有数据冲突时，MySQL **不会创建新纪录（不发生重复入库）**，而是自动对已有记录的公告日期及关键 Fact 字段进行更新：
  ```sql
  ON DUPLICATE KEY UPDATE
      ann_date = VALUES(ann_date),
      f_ann_date = VALUES(f_ann_date),
      total_assets = VALUES(total_assets),
      ...
      updated_at = CURRENT_TIMESTAMP
  ```
- **价值**: 即使脚本重复运行或数据重复推送，也能实现天然的**幂等性**，保证物理表绝无重复冗余行。

### 3.3 第三层：Python 业务层预清洗 (Python-Level Filtering)
在上市公司披露财报的过程中，可能会针对同一报告期发布“更正公告”，导致 Tushare API 一次性返回多条相同 `end_date` 但 `ann_date` 不同的记录。
- **去重算法**:
  1. 在 Python 代码中，将拉取到的 DataFrame 或 List[Dict] 按照唯一标识 `(ts_code, end_date, report_type)` 进行 GroupBy 分组。
  2. 比较同一分组内的 `ann_date`（公告日期）或 `f_ann_date`（实际公告日期），**仅保留最新发布的那一条记录**，剔除已被更正的历史过期重复记录。
  3. 将精简去重后的干净批次提交给 `execute_many` 批量入库，从源头杜绝批次内的主键冲突。

---

## 4. 用户评审要求 (User Review Required)

> [!IMPORTANT]
> **财务回填的破坏性动作与数据安全**:
> 1. **全量回填策略**: 实施中会对 `ods_fin_balancesheet`, `ods_fin_income`, `ods_fin_cashflow`, `ods_fin_indicators` 四张表执行数据清理。为避免生产环境误删，将使用 `ON DUPLICATE KEY UPDATE`（不预先 Truncate，或通过脚本配置项显式激活清空）。
> 2. **未来函数规避**: 回测系统或下游 ADS 指标计算时，必须且只能基于 `ann_date` 检索财报数据，确保时序无未来信息污染。

---

## 5. 开放问题与讨论 (Open Questions)

> [!TIP]
> **关于数据拉取的历史起始时间**:
> - 我们默认将拉取 `stock_basic_info` 中所有状态为 `L` (上市中) 的股票从上市日至今的完整历史季度报表。
> - Tushare 最早可追溯至 1990 年。我们无需传 `start_date` 与 `end_date`，直接传 `ts_code` 即可由 Tushare 返回全量历史财报，保证数据最完整。

---

## 6. 拟进行的变更 (Proposed Changes)

我们将对 `scf-collector` 服务执行模块化升级，增加财务三表及指标数据的处理能力：

### 6.1 数据源组件 (Component: `scf-collector/shared/collectors`)

#### [MODIFY] [tushare_cl.py](file:///home/ubuntu/microservice-stock/scf-collector/shared/collectors/tushare_cl.py)
- **新增异步财务拉取接口**:
  - `fetch_balancesheet(self, ts_code: str)`: 封装同步 pro_api `balancesheet` 接口。
  - `fetch_income(self, ts_code: str)`: 封装同步 pro_api `income` 接口。
  - `fetch_cashflow(self, ts_code: str)`: 封装同步 pro_api `cashflow` 接口.
  - `fetch_fina_indicator(self, ts_code: str)`: 封装同步 pro_api `fina_indicator` 接口。
- **技术规范**: 所有同步接口必须使用 `asyncio.to_thread` 执行，防止阻塞事件循环。

---

### 6.2 数据库访问对象 (Component: `scf-collector/shared/db`)

#### [MODIFY] [dao.py](file:///home/ubuntu/microservice-stock/scf-collector/shared/db/dao.py)
- **新增保存与高效率入库方法**:
  - `save_balancesheet(cls, data: List[Dict[str, Any]]) -> int`: 处理 `total_liab` -> `total_liabilities`, `st_borr` -> `short_term_borrow`, `lt_borr` -> `long_term_borrow` 字段对齐；格式化日期字段；执行 `ON DUPLICATE KEY UPDATE` 幂等写入。
  - `save_income(cls, data: List[Dict[str, Any]]) -> int`: 对齐 `n_income` -> `net_profit`；格式化日期；批量幂等写入。
  - `save_cashflow(cls, data: List[Dict[str, Any]]) -> int`: 对齐 `n_cashflow_act`, `n_cashflow_inv_act`, `n_cash_flows_fnc_act` 字段；格式化日期；批量幂等写入。
  - `save_fina_indicator(cls, data: List[Dict[str, Any]]) -> int`: **核心百分比换算**（`roe`, `roe_dt`, `roa`, `netprofit_margin`, `grossprofit_margin`, `debt_to_assets` 除以 100.0 规范化）；格式化日期；批量幂等写入。

---

### 6.3 盘后回填脚本 (Component: `scf-collector/scripts`)

#### [NEW] [tushare_financial_backfill.py](file:///home/ubuntu/microservice-stock/scf-collector/scripts/tushare_financial_backfill.py)
- **回填控制主脚本**:
  - 初始化数据库连接池、加载 `.env` 变量。
  - 获取 A 股上市股票列表：`SELECT ts_code FROM stock_basic_info WHERE list_status = 'L' ORDER BY ts_code ASC`。
  - 检查 `sync_progress` 进度表中 `task_name='financial_sheets_backfill'` 的状态记录。
  - 循环同步每只股票：
    - 拉取资产负债表、利润表、现金流量表、财务指标。
    - **Python 业务层预去重逻辑**：对拉取回的数据进行时序排重，仅保留每个报告期最新公告记录。
    - 数据清洗、转换与入库（通过 DAO 执行 ON DUPLICATE KEY UPDATE）。
    - 将该股票的同步状态标记为 `completed` 记录至 `sync_progress`，支持故障断点断续。
    - **休眠 `THROTTLE_SLEEP = 1.5`s**。
  - 炫酷 CLI 界面刷新：实时输出同步进度（[当前股票/总股票]，已完成 %，预计剩余耗时，已入库记录数等）。

---

## 7. 验证计划 (Verification Plan)

### 7.1 自动化对账测试
我们将在 `tests/` 目录下开发验证测试，通过 Mock 接口数据 and 真实测试数据库进行：
- **测试用例 1: 字段对齐验证**: 验证 `total_liabilities` 等关键列在入库后映射正确。
- **测试用例 2: 百分比转换规范校验**: 验证 `roe` 原值为 `15.5` 时，入库后查询值绝对等于 `0.1550`。
- **测试用例 3: 幂等防重复测试**: 模拟向同一张表插入完全相同的财报批次 3 次，确认数据行数在第一次后不再增长，无 Duplicate Key 报错。
- **测试用例 4: 断点续传测试**: 模拟在同步中途强行 KeyboardInterrupt 中断，再次启动能从断点股票继续，跳过已完成股票。

### 7.2 手动与物理查验 (MySQL 5.7 直连校验)
在脚本跑批结束后，执行以下高强度数据质量 SQL 审计：
1. **数据无重复性物理自检**:
   ```sql
   SELECT ts_code, end_date, report_type, COUNT(*) 
   FROM ods_fin_income 
   GROUP BY ts_code, end_date, report_type 
   HAVING COUNT(*) > 1;
   ```
   (必须返回 0 行结果，确保没有发生任何重复记录入库)
2. **未来函数防范审计**:
   ```sql
   SELECT COUNT(*) FROM ods_fin_income WHERE ann_date IS NULL OR end_date IS NULL;
   ```
   (必须返回 0，公告日与报告期末均完整)
3. **小数精度自检**:
   ```sql
   SELECT ts_code, end_date, roe FROM ods_fin_indicators WHERE roe > 1.0 LIMIT 5;
   ```
   (必须返回 0，确保 ROE 全部正确除以 100 换算为小数)
4. **空值与空行红线**:
   ```sql
   SELECT COUNT(*) FROM ods_fin_balancesheet WHERE total_assets IS NULL;
   ```
   (统计缺失程度，确保主 Fact 字段基本完整)
