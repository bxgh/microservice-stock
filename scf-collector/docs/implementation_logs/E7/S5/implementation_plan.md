# Implementation Plan - E7-S5: Trading Day Aware Trigger Control

## 1. 需求解析 (Readiness Check)
- **核心逻辑**: 在 SCF 定时任务启动时，优先查询 `trade_cal` 表。若当日 `is_open=0` 且操作不在白名单内，则立即终止执行并返回 skip 状态。
- **依赖认证**: 需确保 `trade_cal` 表已在 `alwaysup` 数据库中存在（已通过 `db_inventory.md` 确认）。
- **角色激活**: [Infra Specialist], [Data Quality Steward], [Security & Code Integrity Auditor].

## 2. 拟改动文件

### [Component] shared/db/dao.py

#### [MODIFY] [dao.py](file:///e:/gitee/microservice-stock/scf-collector/shared/db/dao.py)
- **方法**: `is_trading_day(biz_date: str) -> bool`
- **逻辑**: `SELECT is_open FROM trade_cal WHERE cal_date = %s AND exchange = 'SSE'`
- **备注**: 遵循 `AGENTS.md` 4 节，使用 `Asia/Shanghai` 时间。

### [Component] shared/utils/trading_day.py

#### [NEW] [trading_day.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/trading_day.py)
- **类**: `TradingDayGuard`
- **方法**: `async should_skip(op: str, biz_date: str) -> bool`
- **白名单**: `['sync_calendar']`

### [Component] SCF Functions

#### [MODIFY] [meta_sync/index.py](file:///e:/gitee/microservice-stock/scf-collector/functions/meta_sync/index.py)
- 引入 `TradingDayGuard`。
- 在 `async_handler` 的参数解析后立即执行 `should_skip`。

#### [MODIFY] [daily_quotes/index.py](file:///e:/gitee/microservice-stock/scf-collector/functions/daily_quotes/index.py)
- 同上。

## 3. 验收标准对齐 (Given-When-Then)
参考 [E7_Reliability_Validation.md](file:///e:/gitee/microservice-stock/scf-collector/docs/E7_Reliability_Validation.md#E7-S5) 的 AC1-AC3。

## 4. 验证计划

### 自动化测试
- 运行 `pytest tests/test_trading_day.py` (新建)。
- Mock 数据库返回 `is_open=0` 和 `is_open=1` 两种场景。

### 手动验证
- 手动调用 SCF，参数传入 `{"op": "sync_suspension", "biz_date": "2026-05-01"}`。
- 预期日志输出：`[TradingDayGuard] 2026-05-01 is not a trading day. Skipping op: sync_suspension.`
