# API 端点清单

> **用途**: AI 开发时快速查询可用端点

## BaoStock-API (8001)

### K 线与同步
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/history/kline/{code}` | GET | 获取历史 K 线 |
| `/api/v1/sync/kline/{code}` | POST | 同步个股 K 线 |
| `/api/v1/sync/full` | POST | 全市场 K 线同步 |
| `/api/v1/sync/status` | GET | 获取同步进度 |
| `/api/v1/sync/reset` | POST | 重置同步进度 |

### 复权因子
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/sync/adjust_factor/{code}` | POST | 同步个股复权因子 |
| `/api/v1/sync/adjust_factor/full` | POST | 全市场因子同步 |
| `/api/v1/sync/adjust_factor/status` | GET | 因子同步状态 |

### 数据质量
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/sync/verify/daily` | GET | 每日完整性校验 |
| `/api/v1/sync/verify/weekly` | GET | 周维度统计 |
| `/api/v1/sync/freshness` | GET | 数据时效性指标 |
| `/api/v1/sync/remediate` | POST | 数据补偿修复 |

### 其他
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/valuation/{code}` | GET | PE/PB/PS 估值 |
| `/api/v1/index/cons/{code}` | GET | 指数成分股 |
| `/api/v1/collect/stock_history` | POST | 个股历史校准 |
| `/api/v1/scheduler/jobs` | GET | 定时任务列表 |

---

## AkShare-API (8003)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/finance/{code}` | GET | 财务报表摘要 |
| `/api/v1/valuation/{code}` | GET | 估值指标 |
| `/api/v1/finance/indicators/{code}` | GET | 全量财务指标 |
| `/api/v1/dragon_tiger/daily` | GET | 龙虎榜数据 |
| `/api/v1/industry/stock/{code}` | GET | 个股所属行业 |
| `/api/v1/rank/hot` | GET | 热门股票排行 |

---

## PyWencai-API (8002)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/query` | POST | 问财语义选股 |

---

## 通用端点

所有服务均提供：
- `GET /health` - 健康检查

---

## 调试示例

### 示例 1: 获取 BaoStock 历史 K 线

**Request:**
```bash
curl "http://localhost:8001/api/v1/history/kline/sh.600519?start_date=2024-01-01&frequency=d&adjust=2"
```

**Response:**
```json
[
  {
    "date": "2024-01-02",
    "code": "sh.600519",
    "open": "1700.00",
    "high": "1720.00",
    "low": "1690.00",
    "close": "1710.00",
    "volume": "100500",
    "amount": "172000000",
    "adjustflag": "2"
  }
]
```

### 示例 2: 获取 AkShare 财务摘要

**Request:**
```bash
curl "http://localhost:8003/api/v1/finance/600519"
```

**Response:**
```json
{
  "code": "600519",
  "name": "贵州茅台",
  "total_revenue": 150000000000.0,
  "net_profit": 75000000000.0,
  "report_date": "2024-09-30"
}
```

---

## 变更历史

| 日期 | 变更内容 | 负责人 |
|------|----------|--------|
| 2026-01-07 | 初始创建，收录 25 个端点 | Antigravity AI |

> **最后更新**: 2026-01-07
