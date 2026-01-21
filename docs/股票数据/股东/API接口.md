# 股东数据 API 接口文档

所有接口均由 `stock-manager-api` (Port 8004) 提供，前缀为 `/api/v1/shareholders`。

## 1. 同步接口

### 1.1 同步单只股票
同步指定股票的股东户数和前十大股东数据到数据库。

- **URL**: `POST /sync/{code}`
- **Query 参数**:
  - `all` (bool): 是否同步全量历史。`true` 表示同步上市以来所有数据，`false` (默认) 仅同步近期数据。
- **示例**:
  ```bash
  curl -X POST "http://localhost:8004/api/v1/shareholders/sync/600519?all=true"
  ```
- **响应示例**:
  ```json
  {
    "code": "600519",
    "all_history": true,
    "holder_count_synced": 104,
    "top10_synced": 910,
    "synced_at": "2026-01-21 22:10:50"
  }
  ```

### 1.2 批量同步
- **URL**: `POST /sync-batch`
- **Body**:
  ```json
  {
    "codes": ["600519", "000001", "000002"]
  }
  ```
- **Query 参数**: `all` (同上)

## 2. 查询接口

### 2.1 查询股东户数历史
- **URL**: `GET /count/{code}`
- **Query 参数**:
  - `limit` (int): 返回记录数，默认 100，最大 1000。
- **返回字段**:
  - `date`: 截止日期
  - `count`: 股东户数
  - `change_pct`: 户数变动比例 (%)
  - `avg_market_cap`: 户均持股市值 (元)

### 2.2 查询前十大股东
- **URL**: `GET /top10/{code}`
- **Query 参数**:
  - `date` (string): 截止日期 (YYYY-MM-DD)。如果不传，则返回最新一期数据。
- **返回字段**:
  - `rank`: 排名
  - `holder_name`: 股东名称
  - `hold_pct`: 持股比例 (%)
  - `hold_count`: 持股数量 (股)
  - `share_type`: 股份类型 (如：流通A股)

---

## 3. 底层数据源转发 (akshare-api)
如果需要直接获取原始 JSON 且不入库，可访问 `akshare-api` (Port 8003):
`GET /api/v1/shareholder/{code}?all=true`
