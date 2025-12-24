# 云端数据源 API 需求规格

> 基于 [ADR-002 混合架构决策](file:///home/bxgh/microservice-stock/docs/epics/epic008-hybrid-architecture/ADR-002-混合架构决策.md)

## 概览

| 服务名 | 端口 | 数据源 | 核心功能 |
|--------|------|--------|----------|
| **akshare-api** | 8000 | 东方财富等 | 财务、估值、龙虎榜、行业 |
| **baostock-api** | 8001 | baostock.com:10030 | 复权K线、指数成分、盈利能力 |
| **pywencai-api** | 8002 | 同花顺问财 | 自然语言选股、板块筛选 |

---

## 通用技术要求

### 框架与部署

```yaml
# Docker Compose 配置模板
version: "3.8"
services:
  <service>-api:
    image: python:3.12-alpine
    restart: unless-stopped
    ports:
      - "<port>:8000"
    environment:
      - TZ=Asia/Shanghai
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 128M
```

### 统一 API 规范

| 项目 | 要求 |
|------|------|
| 框架 | FastAPI |
| 响应格式 | JSON |
| 健康检查 | `GET /health` → `{"status": "healthy"}` |
| 错误码 | 4xx 客户端错误, 5xx 服务端错误 |
| 超时 | 30秒 |
| 日志 | JSON 格式, 含 request_id |

---

## akshare-api (:8000)

### 端点清单

| 端点 | 方法 | 功能 | 示例参数 |
|------|------|------|----------|
| `/api/v1/finance/{code}` | GET | 财务报表 | code=600519 |
| `/api/v1/valuation/{code}` | GET | 估值指标 | code=600519 |
| `/api/v1/valuation/{code}/history` | GET | 历史估值 | start_date, end_date |
| `/api/v1/dragon_tiger/daily` | GET | 龙虎榜 | date=2024-01-15 |
| `/api/v1/industry/stock/{code}` | GET | 个股行业 | code=600519 |
| `/api/v1/rank/hot` | GET | 热门排行 | limit=50 |

### 返回字段示例

**`/api/v1/finance/{code}`**:
```json
{
  "code": "600519",
  "total_revenue": 150000000000,
  "net_profit": 75000000000,
  "roe": 0.32,
  "report_date": "2024-09-30"
}
```

**`/api/v1/valuation/{code}`**:
```json
{
  "code": "600519",
  "pe": 28.5,
  "pb": 9.2,
  "ps": 12.1,
  "market_cap": 1800000000000
}
```

---

## baostock-api (:8001)

### 端点清单

| 端点 | 方法 | 功能 | 示例参数 |
|------|------|------|----------|
| `/api/v1/history/kline/{code}` | GET | 历史K线 | frequency=d, adjust=2 |
| `/api/v1/index/cons/{index}` | GET | 指数成分 | index=sz.399300 |
| `/api/v1/industry/classify` | GET | 行业分类 | - |
| `/api/v1/finance/profit/{code}` | GET | 盈利能力 | code=sh.600519 |
| `/api/v1/sync/kline/{code}` | POST | 同步个股至MySQL | start_date, end_date |
| `/api/v1/sync/full` | POST | 一键全市场同步 | start_date |
| `/api/v1/sync/status` | GET | 查看进度 | - |
| `/api/v1/sync/reset` | POST | 重置进度 | - |

### 关键参数说明

**复权类型 (adjust)**:
- `1` = 后复权
- `2` = 前复权
- `3` = 不复权

**K线频率 (frequency)**:
- `d` = 日线
- `w` = 周线
- `m` = 月线
- `5` = 5分钟线

### 返回字段示例

**`/api/v1/history/kline/{code}`**:
```json
[
  {
    "date": "2024-01-15",
    "open": 1680.00,
    "high": 1699.50,
    "low": 1675.00,
    "close": 1695.00,
    "volume": 1234567,
    "amount": 2098765432,
    "turn": 0.12,
    "pctChg": 1.25
  }
]
```

---

## pywencai-api (:8002)

### 端点清单

| 端点 | 方法 | 功能 | 示例参数 |
|------|------|------|----------|
| `/api/v1/query` | POST | 自然语言查询 | q="今日涨停" |
| `/api/v1/sector/hot` | GET | 热门板块 | - |

### 请求示例

**`POST /api/v1/query`**:
```json
{
  "q": "连续3日涨停",
  "perpage": 100
}
```

### 返回字段

> 注意：返回列是动态的，取决于查询内容

```json
{
  "columns": ["股票代码", "股票名称", "涨停天数", "最新价"],
  "data": [
    ["000001", "平安银行", 3, 12.50],
    ["600519", "贵州茅台", 3, 1700.00]
  ]
}
```

### 特殊注意

- **反爬限制**: 需处理验证码失败
- **失败率**: 约 30%
- **频率限制**: ~10次/分钟

---

## 调用方集成

本地 `mootdx-source` 通过 HTTP 代理调用云端 API：

```python
# 环境变量
AKSHARE_API_URL=http://124.221.80.250:8000
BAOSTOCK_API_URL=http://124.221.80.250:8001
PYWENCAI_API_URL=http://124.221.80.250:8002
HTTP_PROXY=http://192.168.151.18:3128
```

---

## 验收标准

- [ ] 健康检查 200 响应
- [ ] 所有端点返回正确 JSON
- [ ] 错误时返回标准错误格式
- [ ] 日志包含 request_id
- [ ] 容器资源 ≤128MB
