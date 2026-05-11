# Mootdx API Specification

**服务名称**: mootdx-api
**端口**: 8007 (外部), 8000 (内部)
**基础路径**: `/api/v1`

## 1. 健康检查

### 1.1 `GET /health`
检查服务健康状态与连接池状态。

**返回示例**:
```json
{
  "status": "healthy",
  "service": "mootdx-api",
  "pool": {
    "pool_size": 3,
    "available": 3,
    "initialized": true,
    "local_ips": [],
    "targets_count": 3,
    "strategy": "list"
  }
}
```

---

## 2. 行情数据接口

### 2.1 获取实时行情 `GET /api/v1/quotes`

获取一组股票的实时快照数据。

**请求参数**:
* `codes` (Query, 必填, string): 股票代码列表，英文逗号分隔（如: `600519,000001` 或 `SH600519,SZ000001`）。

**返回示例**:
```json
[
  {
    "market": 1,
    "code": "600519",
    "price": 1372.99,
    "last_close": 1371.05,
    "open": 1371.66,
    "high": 1382.77,
    "low": 1370.0,
    "vol": 33368,
    "amount": 4582856192.0,
    "servertime": "14:51:46.447",
    ...
  }
]
```

---

### 2.2 获取分笔成交 `GET /api/v1/tick/{code}`

获取个股当天的分笔成交明细（Tick Data）。

**请求参数**:
* `code` (Path, 必填, string): 股票代码（如 `600519`）。
* `date` (Query, 选填, int): 交易日期（YYYYMMDD格式，如 `20260508`。若不传默认当日）。
* `start` (Query, 选填, int): 起始位置（默认 `0`）。
* `offset` (Query, 选填, int): 获取数量（范围 `1-10000`，默认 `800`）。

**返回示例**:
```json
[
  {
    "time": "14:56",
    "price": 1371.5,
    "volume": 1200,
    "type": "BUY",
    "num": 11
  }
]
```

---

### 2.3 获取历史K线 `GET /api/v1/history/{code}`

获取个股历史 OHLCV K线数据。

**请求参数**:
* `code` (Path, 必填, string): 股票代码（如 `600519`）。
* `frequency` (Query, 选填, string): K线频率，可选值 `d` (日线，默认), `w` (周线), `m` (月线)。
* `offset` (Query, 选填, int): 获取条数（最大 `800`，默认 `500`）。

**返回示例**:
```json
[
  {
    "datetime": "2026-05-08 15:00",
    "open": 1371.66,
    "close": 1372.99,
    "high": 1382.77,
    "low": 1370.0,
    "vol": 33368.0,
    "amount": 4582856192.0,
    "volume": 33368.0
  }
]
```

---

### 2.4 获取指数K线 `GET /api/v1/index/bars/{code}`

获取指数的 OHLCV K线数据。

**请求参数**:
* `code` (Path, 必填, string): 指数代码（必须带市场前缀以防歧义，如 `SH000001` 代表上证指数）。
* `frequency` (Query, 选填, string): 频率 `d`, `w`, `m` (默认 `d`)。
* `offset` (Query, 选填, int): 条数 (最大 `800`，默认 `500`)。

**返回示例**:
```json
[
  {
    "datetime": "2026-05-08 15:00",
    "open": 4163.85,
    "close": 4179.95,
    "high": 4183.06,
    "low": 4154.25,
    "vol": 6970190.0,
    "amount": 1331673038848.0,
    "up_count": 1441,
    "down_count": 842,
    "volume": 6970190.0
  }
]
```

---

## 3. 基础信息接口

### 3.1 获取股票列表 `GET /api/v1/stocks`

获取 A 股市场股票代码列表。

**请求参数**:
* `market` (Query, 选填, int): 市场编码 `0`=深圳，`1`=上海。不传返回全市场。

---

### 3.2 获取财务基础信息 `GET /api/v1/finance/{code}`

获取个股流通股本、总股本等财务基础信息。

**请求参数**:
* `code` (Path, 必填, string): 股票代码。

---

### 3.3 获取除权除息数据 `GET /api/v1/xdxr/{code}`

获取个股历史除权除息及分红配股数据，可用于前复权计算。

**请求参数**:
* `code` (Path, 必填, string): 股票代码。

---

## 4. 全局规范
* **错误响应**: 当发生错误时，返回标准的 JSON 格式：`{"detail": "Error Message"}`
* **请求追踪**: 所有接口均支持从 Header 接收并返回 `X-Request-ID`，用于链路追踪。未提供时系统自动生成并附在响应头中。
