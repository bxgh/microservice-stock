# API 接口文档 - E200-S2: 自愈修复引擎 (Healer)

## 1. 基础信息
- **服务名称**: `stock-manager-api`
- **基础路径**: `/api/v1/healer`
- **权限控制**: 内部管理权限
- **数据格式**: JSON

---

## 2. 接口定义

### 2.1 触发自动修复扫描
启动对 `dq_findings` 的扫描并执行建议的修复。

- **URL**: `/repair`
- **Method**: `POST`
- **Query Params**:
  - `limit` (int, default=10): 本次扫描处理的最大异常数量。
- **Response** (202 Accepted):
```json
{
  "status": "accepted",
  "message": "正在后台处理最多 10 条异常记录"
}
```

### 2.2 修复指定异常项
针对特定的 `finding_id` 执行单条修复。

- **URL**: `/repair/{finding_id}`
- **Method**: `POST`
- **Response** (200 OK):
```json
{
  "status": "success",
  "message": "异常 9123 已修复"
}
```

### 2.3 一键回滚修复
根据修复日志 ID 撤销之前的修复操作。

- **URL**: `/rollback/{repair_id}`
- **Method**: `POST`
- **Response** (200 OK):
```json
{
  "status": "success",
  "message": "修复记录 5 已成功回滚"
}
```

### 2.4 查询修复日志
获取自愈修复的历史审计记录。

- **URL**: `/logs`
- **Method**: `GET`
- **Query Params**:
  - `limit` (int, default=20): 返回记录条数。
- **Response** (200 OK):
```json
{
  "logs": [
    {
      "id": 5,
      "finding_id": 9123,
      "ts_code": "600519.SH",
      "trade_date": "2026-05-08",
      "table_name": "stock_kline_daily",
      "repair_type": "CONSENSUS",
      "source_used": "MOOTDX",
      "status": "SUCCESS",
      "created_at": "2026-05-10T23:45:00"
    }
  ]
}
```

---

## 3. 错误码说明
| 状态码 | 错误码 (Code) | 说明 |
| :--- | :--- | :--- |
| 400 | BAD_REQUEST | 参数错误或回滚状态不符合要求 |
| 500 | INTERNAL_ERROR | 修复执行失败（如源数据无法获取） |
| 503 | SERVICE_UNAVAILABLE | 下游补数源（Mootdx-api 等）连接超时 |
