# 股票数据消息类型清单

| 消息类型 (Type) | 中文名称 | 状态 | 服务 (Port) | 核心接口 (Core API) | 验证结果 (2026-01-16) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `kline` | K线数据 | ✅ | baostock (8001) | `GET /api/v1/history/kline/{code}` | ✅ Pass |
| `financial` | 财务数据 | ✅ | akshare (8003) | `GET /api/v1/finance/{code}`<br>`GET /api/v1/finance/indicators/{code}` | ✅ Pass |
| `valuation` | 估值指标 | ✅ | akshare (8003)<br>baostock (8001) | `GET /api/v1/valuation/{code}` (实时)<br>`GET /api/v1/valuation/{code}/history` (历史) | ✅ Pass |
| `top_list` | 龙虎榜 | ✅ | akshare (8003) | `GET /api/v1/dragon_tiger/daily` | ✅ Pass |
| `sector` | 板块/行业 | ✅ | akshare (8003)<br>pywencai (8002) | `GET /api/v1/industry/stock/{code}`<br>`GET /api/v1/sector/hot` | ✅ Pass |
| `capital_flow` | 资金流向 | ✅ | akshare (8003) | `GET /api/v1/capital_flow/{code}` | ✅ Pass |
| `block_trade` | 大宗交易 | ✅ | akshare (8003) | `GET /api/v1/block_trade/daily` | ✅ Pass |
| `margin` | 融资融券 | ✅ | akshare (8003) | `GET /api/v1/margin/{code}` | ✅ Pass |
| `shareholder` | 股东数据 | ✅ | akshare (8003) | `GET /api/v1/shareholder/{code}` | ✅ Pass |
| `dividend` | 分红配股 | ✅ | akshare (8003) | `GET /api/v1/dividend/{code}` | ✅ Pass |
| `suspension` | 停复牌 | ✅ | akshare (8003) | `GET /api/v1/suspension/daily` | ✅ Pass |

| `announcement` | 公告 | ⚠️ | - | - | - |

---

## 接口调用与返回示例

### 1. K线数据 (`kline`)
*   **服务**: `baostock (8001)`
*   **方法**: `GET /api/v1/history/kline/{code}`
*   **参数**: `frequency` (d/w/m/5/15/30/60), `adjust` (1-后复权, 2-前复权, 3-不复权)
*   **示例**:
    ```json
    [
      {
        "date": "2024-01-16",
        "open": 1650.0,
        "high": 1700.0,
        "low": 1640.0,
        "close": 1680.0,
        "volume": 25000,
        "amount": 42000000.0,
        "turn": 0.15,
        "pctChg": 1.2
      }
    ]
    ```

### 2. 财务数据 (`financial`)
*   **服务**: `akshare (8003)`
*   **方法**: `GET /api/v1/finance/{code}`
*   **返回**: 核心财务指标摘要
*   **示例**:
    ```json
    {
      "total_revenue": 130904000000.0,
      "net_profit": 64627000000.0,
      "roe": 0.2464,
      "report_date": "2025-09-30",
      "code": "600519"
    }
    ```

### 3. 估值指标 (`valuation`)
*   **服务**: `akshare (8003)`
*   **方法**: `GET /api/v1/valuation/{code}`
*   **示例**:
    ```json
    {
      "name": "贵州茅台",
      "pe": 20.08,
      "pb": 7.62,
      "market_cap": 1730637437130.0,
      "price": 1382.0,
      "code": "600519"
    }
    ```

### 4. 股东数据 (`shareholder`)

#### 数据获取 (akshare-api)
*   **服务**: `akshare (8003)`
*   **方法**: `GET /api/v1/shareholder/{code}` (可选参数: `?all=true` 获取上市以来完整数据)
*   **返回**: 包含股东户数历史及前十大流通股东
*   **示例**:
    ```json
    {
      "holder_count_history": [
        { "date": "2025-09-30", "count": 238512, "change": 8.0913, "avg_market_cap": 7454505.01114879 }
      ],
      "top10_holders": [
        { 
          "rank": 1, 
          "holder_name": "中国贵州茅台酒厂(集团)有限责任公司", 
          "share_type": "流通A股", 
          "hold_count": 680424580, 
          "hold_pct": 54.33, 
          "change": "415879", 
          "time": "2025-11-19" 
        }
      ]
    }
    ```

#### 数据同步与查询 (stock-manager-api)
*   **服务**: `stock-manager (8004)`
*   **数据库**: MySQL (`stock_shareholder_count`, `stock_top10_shareholders`)
*   **同步接口**:
    *   `POST /api/v1/shareholders/sync/{code}?all=true` - 同步单只股票 (支持全量/增量)
    *   `POST /api/v1/shareholders/sync-batch` - 批量同步 (请求体: `{"codes": ["600519", "000001"]}`)
*   **查询接口**:
    *   `GET /api/v1/shareholders/count/{code}?limit=100` - 查询股东户数历史
    *   `GET /api/v1/shareholders/top10/{code}?date=2025-09-30` - 查询前十大股东 (可指定日期)
*   **验证**: ✅ 2026-01-21 (已同步茅台 104 期户数 + 910 条前十大股东记录)

### 5. 资金流向 (`capital_flow`)
*   **服务**: `akshare (8003)`
*   **方法**: `GET /api/v1/capital_flow/{code}`
*   **示例**:
    ```json
    [
      {
        "date": "2025-07-22",
        "close": 1441.02,
        "main_net_inflow": 781613248.0,
        "main_net_inflow_pct": 12.76,
        "super_large_net_inflow": 568975264.0
      }
    ]
    ```

### 6. 分红配股 (`dividend`)
*   **服务**: `akshare (8003)`
*   **方法**: `GET /api/v1/dividend/{code}`
*   **示例**:
    ```json
    [
      {
        "report_date": "2023-12-31",
        "plan_date": "2024-04-01",
        "bonus_share_ratio": 0.0,
        "cash_dividend_ratio": 30.87,
        "progress": "实施分配"
      }
    ]
    ```

### 7. 停复牌信息 (`suspension`)
*   **服务**: `akshare (8003)`
*   **方法**: `GET /api/v1/suspension/daily`
*   **参数**: `date` (YYYY-MM-DD，获取指定日期或最新的停牌列表)
*   **示例**:
    ```json
    [
      {
        "code": "603980",
        "name": "吉华集团",
        "suspension_date": "2026-02-02",
        "resumption_date": null,
        "reason": "刊登重要公告",
        "market": "上交所主板"
      }
    ]
    ```

#### 数据同步 (stock-manager-api)
*   **同步接口**: `POST /api/v1/suspensions/sync`
    *   参数: `start_date`, `end_date` (YYYY-MM-DD)
    *   功能: 从 BaoStock 获取历史每日停牌状态 (`tradeStatus=0`) 并存入 MySQL `stock_suspensions` 表。