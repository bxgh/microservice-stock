# API Specification - E400-S1 (Internal Operations)

## 1. daily_quotes 函数新增操作

### op: `sync_kline_daily`
- **描述**: 批量同步全 A 股票单日日 K 线。
- **参数**:
  - `trade_date`: 交易日期 (YYYY-MM-DD)
- **返回**: `{"status": "success", "count": N, "request_id": "..."}`

### op: `sync_adj_factor`
- **描述**: 批量同步单日复权因子。
- **参数**:
  - `trade_date`: 交易日期 (YYYY-MM-DD)
- **返回**: `{"status": "success", "count": N, "request_id": "..."}`

### op: `sync_index_daily`
- **描述**: 同步指定指数行情。
- **参数**:
  - `trade_date`: 交易日期 (YYYY-MM-DD)
  - `ts_codes`: 指数代码列表 (逗号分隔，默认含上证、深证、创业板、沪深 300 等)
- **返回**: `{"status": "success", "count": N, "request_id": "..."}`

---

## 2. meta_sync 函数新增操作

### op: `sync_sw_industry_member`
- **描述**: 全量同步申万行业成员拉链数据。
- **参数**: 无 (同步全量)
- **返回**: `{"status": "success", "count": N, "request_id": "..."}`
