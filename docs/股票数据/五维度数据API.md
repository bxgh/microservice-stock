# 股东数据 API 接口文档

所有接口均由 `stock-manager-api` (Port 8004) 提供，前缀为 `/api/v1/shareholders`。

> **注意**: 为确保跨表关联一致性，所有接口的代码参数（`{code}`）均应遵循标准后缀格式（如 `600519.SH`）。虽然系统会尝试自动转换纯数字代码，但建议调用方优先传入标准格式。

## 1. 同步接口

### 1.1 同步单只股票
同步指定股票的股东户数和前十大股东数据到数据库。

- **URL**: `POST /sync/{code}`
- **Query 参数**:
  - `all` (bool): 是否同步全量历史。`true` 表示同步上市以来所有数据，`false` (默认) 仅同步近期数据。
- **示例**:
  ```bash
  curl -X POST "http://localhost:8004/api/v1/shareholders/sync/600519.SH?all=true"
  ```
- **响应示例**:
  ```json
  {
    "code": "600519.SH",
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
    "codes": ["600519.SH", "000001.SZ", "000002.SZ"]
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

## 3. 筹码维度 (Chips) API
前缀: `/api/v1/chips`

### 3.1 同步限售解禁
- **URL**: `POST /sync/restricted`
- **Query 参数**:
  - `start_date` (string): 开始日期 (YYYY-MM-DD)，可选。
  - `end_date` (string): 结束日期 (YYYY-MM-DD)，可选。
- **说明**: 同步指定时间段的限售股解禁计划。

### 3.2 同步大宗交易
- **URL**: `POST /sync/block_trade`
- **Query 参数**:
  - `date` (string): 单日同步日期 (YYYY-MM-DD)。
  - `start_date`, `end_date` (string): 范围同步。
- **说明**: 同步大宗交易明细。

## 4. 博弈维度 (Game) API
前缀: `/api/v1/game`

### 4.1 同步龙虎榜
- **URL**: `POST /sync/lhb`
- **Query 参数**: `date` (YYYY-MM-DD)
- **说明**: 同步当日龙虎榜全榜及机构买卖统计。

### 4.2 同步北向资金 (每日快照)
- **URL**: `POST /sync/north`
- **Query 参数**: `date` (YYYY-MM-DD)
- **说明**: 基于交易所最新披露的“今日排行”获取持股快照。

### 4.3 同步北向资金 (个股历史)
- **URL**: `POST /sync/north/history/{code}`
- **说明**: 同步指定股票的历史北向持股数据 (2016年至今)。

---

## 5. 底层数据源转发 (akshare-api)
如果需要直接获取原始 JSON 且不入库，可访问 `akshare-api` (Port 8003):
- 股东: `GET /api/v1/shareholder/{code}?all=true`
- 大宗: `GET /api/v1/block_trade/daily?date=...`
- 龙虎榜: `GET /api/v1/dragon_tiger/daily?date=...`
- 北向: `GET /api/v1/north/daily?date=...`
