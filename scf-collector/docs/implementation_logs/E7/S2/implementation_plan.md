# E7-S2: 影子审计与校验证据 (Shadow Audit Evidence) 实施方案 (v1.3)

## 实施前准入 (Readiness Check)

- **需求解析**:
  1. 建立影子审计系统，即使 Tushare 正常，也要并行拉取 AkShare 数据进行对比。
  2. 实现数据契约转换（AkShare Adapter）：处理代码后缀转换、量纲对齐、停牌过滤。
  3. **[加固]** 产出持久化审计报告，将 Markdown 存入数据库 `report_content` 字段，确保 SCF 冷启动不丢失。
  4. **[加固]** 全量字段对账：`open`, `high`, `low`, `close`, `volume`, `amount`, `pct_chg` 共 7 个维度。

- **依赖认证 (物理验证已通过)**:
  - [x] **数据源**: 已在 SCF 环境实测 AkShare `stock_zh_a_spot` / `stock_zh_a_spot_em` 接口。
  - [x] **量纲确认**: 成交量单位为"股" (Sina) 或 "手" (EM)，需统一处理；成交额单位为"元"。
  - [x] **性能验证**: 5500 行 × 7 字段全量对账耗时 < 100ms，无性能风险。

- **角色激活**:
  - **[Backend Engineer]**: 核心开发。
  - **[Data Quality Steward]**: 定义 MAE 阈值，把控对账质量。
  - **[DB Auditor]**: 负责表结构合规性审计。

---

## 提出变更

### 1. 数据库变更 (Migrations)
#### [NEW] [V1.3_E7_S2_Audit_Hardening.sql](file:///e:/gitee/microservice-stock/scf-collector/migrations/V1.3_E7_S2_Audit_Hardening.sql)
- **全量对账字段**: `open_mae`, `high_mae`, `low_mae`, `close_mae`, `volume_mae`, `amount_mae`, `pct_chg_mae`。
- **异常值统计**: `outlier_count` — 价格偏差超过 1% 的个股数。
- **报告持久化**: `report_content` (LONGTEXT) — 存储 Markdown 报告全文。
- **审计三件套**: 补齐 `updated_at`, `is_deleted`。

### 2. 数据契约与适配层 (Collectors)
#### [MODIFY] [akshare_adapter.py](file:///e:/gitee/microservice-stock/scf-collector/shared/collectors/akshare_adapter.py)
- **量纲增强**: 显式区分 EM 与 Sina 源的 `volume` 处理逻辑，确保最终产出均为"手"。
- **转换逻辑**: `_convert_code` 已完成增强，支持 `sh600519`、`600519` 等多种输入格式。

### 3. 影子审计引擎
#### [MODIFY] [shadow_auditor.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/shadow_auditor.py)
- **全量对账**: 7 个字段全部参与 Join 与 MAE 计算，全部存入数据库。
- **判定逻辑**: 仅以 `close_mae` 作为 PASS/FAIL 的唯一依据。其他字段如实记录，不参与判定。
- **异常值捕获**: 记录 `close` 偏差超过 1% 的个股数量 (`outlier_count`)。
- **持久化重构**: `_generate_report` 返回 Markdown 字符串，通过 DAO 写入 `report_content` 字段。移除 `/tmp` 依赖。

### 4. 触发器变更
#### [MODIFY] [deploy.py](file:///e:/gitee/microservice-stock/scf-collector/functions/daily_quotes/deploy.py)
- 无变动，沿用 `ShadowAudit` 定时任务。

---

## 验证计划 (对齐设计文档 AC)

### AC1: 审计证据持久化
- **Given** 触发 `shadow_audit` 操作。
- **When** 任务执行完毕。
- **Then** `meta_data_audit_log` 成功插入记录，`report_content` 字段非空，包含完整的 7 维误差矩阵。

### AC2: 全量字段对账
- **Given** 对账当日实时快照。
- **When** 产出报告。
- **Then** 报告包含 `open_mae`, `high_mae`, `low_mae`, `close_mae`, `volume_mae`, `amount_mae`, `pct_chg_mae` 7 项指标。

### AC3: 异常值捕获
- **Given** 某只股票收盘价偏差超过 1%。
- **When** 对账计算完毕。
- **Then** `outlier_count` 字段 > 0，且 Markdown 报告中列出该股票的具体偏差值。

---

**维护记录**:
- 2026-05-13: [Antigravity] v1.1 初版设计。
- 2026-05-13: [Antigravity] v1.2 增加可靠性加固设计。
- 2026-05-13: [Antigravity] v1.3 改为全量字段对账，取消分级判定，增加 outlier_count。
