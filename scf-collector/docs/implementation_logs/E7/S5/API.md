# API Changes - E7-S5: Trading Day Aware Trigger Control

## 1. 响应状态扩展 (Response Status Extension)

所有受 `TradingDayGuard` 保护的接口（`meta_sync`, `daily_quotes`）在非交易日调用时增加以下标准返回：

### 状态: 跳过执行 (Skipped)
- **触发条件**: 业务日期为非交易日，且 `op` 不在白名单内。
- **HTTP Code**: 200 (SCF Handler 层面返回成功)
- **Payload**:
```json
{
    "status": "skipped",
    "reason": "not_a_trading_day",
    "op": "sync_suspension",
    "biz_date": "2026-05-01",
    "request_id": "..."
}
```

## 2. 准入逻辑说明
- **白名单操作**: `sync_calendar`, `verify`, `migrate`。这些操作即使在非交易日也会正常执行。
- **校验源**: 数据库 `trade_cal` 表，`exchange='SSE'`。
