
# 数据审计日志接口 (Data Audit)

## 1. 概述
提供对 `data_audit_summaries` 和 `data_audit_details` 表的查询接口，用于监控数据质量问题。

## 2. 接口列表

### 2.1 获取审计汇总列表
*   **URL**: `/api/v1/data-audits`
*   **Method**: `GET`
*   **Tags**: `数据审计`
*   **Parameters**:

| 参数名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| page | int | 否 | 页码，默认1 |
| size | int | 否 | 每页条数，默认20 |
| trade_date | str | 否 | 交易日 (YYYY-MM-DD) |
| data_type | str | 否 | 数据类型 (如 'daily_kline') |
| level | str | 否 | 告警级别 (INFO/WARNING/ERROR) |

*   **Response**: `200 OK`

```json
{
  "items": [
    {
      "id": 1001,
      "data_type": "daily_kline",
      "target": "stocks_all",
      "trade_date": "2024-01-15",
      "level": "WARNING",
      "issue_count": 5,
      "description": "5 stocks missing",
      "created_at": "2024-01-15T18:00:00",
      "updated_at": "2024-01-15T18:00:00"
    }
  ],
  "total": 100,
  "page": 1,
  "size": 20
}
```

### 2.2 获取单个汇总详情
*   **URL**: `/api/v1/data-audits/{id}`
*   **Method**: `GET`
*   **Response**: `200 OK`

```json
{
  "id": 1001,
  "data_type": "daily_kline",
  "target": "stocks_all",
  "trade_date": "2024-01-15",
  "level": "WARNING",
  "issue_count": 5,
  "description": "5 stocks missing",
  "created_at": "2024-01-15T18:00:00",
  "updated_at": "2024-01-15T18:00:00"
}
```

### 2.3 获取审计详情记录
*   **URL**: `/api/v1/data-audits/{id}/details`
*   **Method**: `GET`
*   **Response**: `200 OK`

```json
{
  "items": [
    {
      "id": 5001,
      "summary_id": 1001,
      "dimension": "completeness",
      "level": "ERROR",
      "message": "Stock 600000 missing data",
      "context": { "code": "600000" },
      "created_at": "2024-01-15T18:00:01"
    }
  ]
}
```
