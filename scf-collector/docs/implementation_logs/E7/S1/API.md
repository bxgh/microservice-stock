# API Documentation - stock-scf-meta

`stock-scf-meta` 是一个基于事件驱动的微服务，用于同步股票市场基础元数据。

## 1. 函数信息
- **函数名称**: `stock-scf-meta`
- **运行环境**: Python 3.10
- **入口**: `index.main_handler`

## 2. 调用接口 (Event Schema)

调用时需传入 JSON 格式的 Event 对象。

### 2.1 同步交易日历 (`sync_calendar`)
- **参数**:
    - `op`: "sync_calendar" (必填)
    - `biz_date`: 业务日期 (可选, 默认当天)
- **描述**: 从 Tushare 抓取前后 1 年的交易日历并更新至 `trade_cal`。

### 2.2 同步股票列表 (`sync_stock_list`)
- **参数**:
    - `op`: "sync_stock_list" (必填)
- **描述**: 从 Tushare 抓取全市场上市股票列表并更新至 `stock_basic_info`。

## 3. 响应格式

```json
{
    "status": "success",
    "op": "sync_calendar",
    "count": 13162,
    "request_id": "uuid-xxx-xxx"
}
```

## 4. 触发建议
- **定时触发器 1**: `0 30 8 * * * *` (每日 08:30 执行日历同步)
- **定时触发器 2**: `0 0 9 * * * *` (每日 09:00 执行股票列表同步)
