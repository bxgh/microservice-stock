# Implementation Plan - E12-S1-T1

## 实施前认证 (Readiness Check)
- [x] **需求解析**: 3句话描述核心逻辑。 (开发具备“三源仲裁”能力的像素级巡检脚本，实现 stock_kline_daily 与 stock_adjust_factor 的全量准确性审计。)
- [x] **结构化设计**: 必须使用 epic-story-doc 生成 draft_E12.md 并在微服务 docs 下。
- [x] **依赖认证**: 查实 TABLES_INDEX.md 及环境连通性。
- [x] **角色激活**: 显式声明激活的角色。

开发具备“三源仲裁”能力的像素级巡检脚本，实现 `stock_kline_daily` 与 `stock_adjust_factor` 的全量准确性审计。

## 角色激活
- **[Data Integrity Steward]**: 负责三源仲裁逻辑设计与数据质量门禁。
- **[Python Backend Engineer]**: 负责高性能对账引擎实现。

## 需求解析
1. **全量像素级对账**：不仅检查数据缺失（Hole），还需 1:1 比对 OHLC 及成交量数值。
2. **三源对账仲裁**：当 `Local != Tushare` 时，自动引入 `AkShare` 作为第三方证人进行仲裁。
3. **双表覆盖**：同步校验 `stock_kline_daily` (K线) 与 `stock_adjust_factor` (因子)。

## 依赖认证
- **数据源**: 
    - Tushare (P0): 每日行情接口 (`daily`)
    - AkShare (P1): 历史行情接口 (`stock_zh_a_hist`)
- **数据库表**:
    - `stock_kline_daily`: 审计目标 A
    - `stock_adjust_factor`: 审计目标 B
    - `meta_trading_calendar`: 对账时间基准
- **性能红线**:
    - 内存: < 192MB (使用 Daily Chunking 模式，每次处理一日数据)
    - 频率: Tushare QPS 限制 (按 2000 积分配置)

## 核心规则：三源对账过滤与对齐逻辑

为了消除不同数据源之间的系统性差异，巡检脚本必须严格遵守以下过滤逻辑：

### 1. 不复权口径对齐 (Raw Data Alignment)
- **强制约束**：所有比对（本地、Tushare、AkShare）必须强制使用 **“不复权” (Unadjusted/Raw)** 价格。
- **理由**：不复权 OHLC 是交易所的物理真值，不含任何算法漂移。AkShare 调用必须指定 `adjust=""`。

### 2. 停牌日处理 (Suspension Logic)
- **对齐基准**：以 `meta_trading_calendar` 为主索引。
- **过滤规则**：若本地缺失某日记录，但经核实该股当天处于“停牌”状态（Tushare 无记录且 AkShare 成交量为 0），则：
    - **判定**：视为“合规缺失”，不记录为 Hole。
    - **例外**：若本地有记录但成交量 > 0（数据污染），则记录为 `redundant_error`。

### 3. 特殊股息与计算偏差 (Special Dividend & Drift)
- **除权日对冲**：在 `stock_adjust_factor` 校验中，若发现因子差异，优先检查是否为“特殊股息”发放日。
- **容错处理**：对于不影响价格序列连续性的极小因子差异（< 0.0001），记录为 `Precision_Drift` 而非 `Error`。

### 4. 断点续传与进度管理 (Checkpoint)
- **存储**：`meta_config` 表中 `kline_audit_cursor` 键值。
- **格式**：`YYYYMMDD` 字符串，代表已完整校验并入库的最后交易日。
- **逻辑**：单日巡检成功后原子更新，重启时自动续传。

### 5. 任务队列定义 (Task Queue Schema)
识别出的 Hole 或 Mismatch 必须标准化入库，供后续修复：
```sql
CREATE TABLE IF NOT EXISTS `meta_task_queue` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `task_type` VARCHAR(32) NOT NULL COMMENT 'REPAIR_KLINE / REPAIR_FACTOR',
  `ts_code` VARCHAR(16) NOT NULL,
  `trade_date` DATE NOT NULL,
  `error_type` ENUM('HOLE', 'PRICE_MISMATCH', 'VOLUME_MISMATCH', 'FACTOR_STALE') NOT NULL,
  `context` JSON COMMENT '存储对账细节,如 {"local": 10.1, "target": 10.0, "source": "Tushare"}',
  `status` ENUM('PENDING', 'RUNNING', 'SUCCESS', 'FAILED') DEFAULT 'PENDING',
  `retry_count` TINYINT DEFAULT 0,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_status_type` (`status`, `task_type`),
  INDEX `idx_code_date` (`ts_code`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 6. 审计报告结构 (REPORT.html)
- **看板 (Dashboard)**：汇总总行数、Gap 率、Mismatch 率、自动推修数。
- **矩阵 (Matrix)**：按月/年展示错误分布热力图。
- **抽样 (Details)**：前 100 条三源差异详细数据对比。

## 拟议变更

### [scf-collector]

#### [NEW] [scripts/audit/kline_integrity_checker.py](file:///home/ubuntu/microservice-stock/scf-collector/scripts/audit/kline_integrity_checker.py)
- **Daily Chunking**: 严格按交易日遍历，单日处理全市场 ~5300 只股票。
- **Arbitration Engine**: 实现 `Local vs Tushare` -> (if mismatch) -> `AkShare` 的二阶段仲裁逻辑。
- **Repair Trigger**: 识别出的 `Hole` 或 `Value_Mismatch` 自动写入 `meta_task_queue`。

## 验证计划

### 自动化测试
- 模拟“本地数据被篡改”场景，验证脚本是否能通过 AkShare 成功纠偏。
- 验证在停牌日期下的自动跳过逻辑。

### 手动验证
- 查看 `REPORT.html` 中的差异分布矩阵，确认不复权对齐无误。
