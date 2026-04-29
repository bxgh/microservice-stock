# 微信小程序调用指南：WXCH Gateway API

本指南旨在帮助前端开发人员在微信小程序中通过“微信云托管”调用重构后的 `wxch-gateway` 服务。

## 1. 基础信息

*   **服务名称**: `wxch-gateway`
*   **环境类型**: 微信云托管 (WeChat CloudBase)
*   **通信协议**: HTTPS (云托管自动处理)
*   **Base URL**: 
    *   **开发环境**: `http://[service-id].tencentcloudcontainer.com`
    *   **正式环境**: `https://[custom-domain-or-service-id].tencentcloudcontainer.com`

## 2. 核心接口：个股 K 线数据

获取个股的历史日 K 线数据。

### 请求信息
*   **路径**: `/api/v1/stocks/{code}/kline`
*   **方法**: `GET`
*   **参数**:
    | 参数名 | 类型 | 必选 | 说明 | 示例 |
    | :--- | :--- | :--- | :--- | :--- |
    | `code` | `string` | 是 | 股票代码，支持 `600519.SH`, `000001.SZ` 或 `sh.600519` | `600519.SH` |
    | `frequency` | `string` | 否 | 频率：`d` (日线, 默认), `w` (周线), `m` (月线), `y` (年线) | `w` |
    | `adjust` | `string` | 否 | 复权：`2` (前复权, 默认), `1` (后复权), `3` (不复权) | `2` |
    | `limit` | `int` | 否 | 返回数据条数，默认 500，最大 1000 | `100` |
    | `start_date` | `string` | 否 | 开始日期 (YYYY-MM-DD) | `2024-01-01` |
    | `end_date` | `string` | 否 | 结束日期 (YYYY-MM-DD) | `2024-12-31` |

### 响应示例 (Success 200)
```json
{
  "code": "600519.SH",
  "frequency": "w",
  "adjust": "2",
  "data": [
    {
      "date": "2024-12-13",
      "open": 1500.0,
      "high": 1520.0,
      "low": 1495.0,
      "close": 1510.5,
      "pre_close": 1490.0,
      "volume": 25000.0,
      "amount": 37762500.0,
      "turnover": 0.15,
      "pct_chg": 1.38,
      "trade_status": 1
    }
  ]
}
```

## 3. 实时行情接口

获取股票的最新价格、涨跌幅等核心行情数据。

### 请求信息
*   **路径**: `/api/v1/stocks/{code}/spot`
*   **方法**: `GET`
*   **响应示例**:
```json
{
  "data": {
    "code": "600519",
    "name": "贵州茅台",
    "last": 1510.5,
    "open": 1500.0,
    "high": 1520.0,
    "low": 1495.0,
    "prev_close": 1490.0,
    "chg": 20.5,
    "chg_pct": 1.38,
    "volume": 25000,
    "amount": 37762500,
    "timestamp": 1713840000
  }
}
```

## 4. 快照行情接口

获取股票的详细快照，包含五档买卖盘口、估值指标与市值。

### 请求信息
*   **路径**: `/api/v1/stocks/{code}/snapshot`
*   **方法**: `GET`
*   **响应示例**:
```json
{
  "data": {
    "code": "600519",
    "name": "贵州茅台",
    "last": 1415.88,
    "open": 1408.0,
    "high": 1419.7,
    "low": 1405.1,
    "prev_close": 1409.5,
    "chg": 6.38,
    "chg_pct": 0.45,
    "volume": 2432800.0,
    "amount": 3437590000.0,
    "timestamp": 1745377800,
    "bid_ask": {
      "buy": [
        {"price": 1415.78, "volume": 200},
        {"price": 1415.77, "volume": 1200},
        {"price": 1415.76, "volume": 300},
        {"price": 1415.73, "volume": 100},
        {"price": 1415.52, "volume": 100}
      ],
      "sell": [
        {"price": 1416.24, "volume": 300},
        {"price": 1416.25, "volume": 200},
        {"price": 1416.30, "volume": 200},
        {"price": 1416.32, "volume": 100},
        {"price": 1416.43, "volume": 100}
      ]
    },
    "pe_dynamic": 21.54,
    "pb": 7.25,
    "market_cap": 17730.64,
    "float_market_cap": 17730.64,
    "turnover_rate": 0.3,
    "turnover_real": 0.62,
    "quantity_ratio": 0.91
  }
}
```

## 5. 分时行情接口

获取个股当日的分时价格点阵及实时统计数据。

### 请求信息
*   **路径**: `/api/v1/stocks/{code}/time_share`
*   **方法**: `GET`
*   **响应示例**:
```json
{
  "code": "600519.SH",
  "turnover_rate": 0.3,
  "turnover_real": 0.62,
  "quantity_ratio": 0.91,
  "data": [
    {
      "time": "0930",
      "price": 1408.0,
      "avg_price": 1408.0,
      "volume": 515.0,
      "amount": 72512000.0
    },
    {
      "time": "0931",
      "price": 1409.5,
      "avg_price": 1408.64,
      "volume": 703.0,
      "amount": 99060735.6
    }
  ]
}
```

## 6. 个股详细信息接口 (MySQL)

以下接口均基于 MySQL 数据库，提供个股的深度多维数据。

### 6.1 基本面 (Fundamentals)
*   **路径**: `/api/v1/stocks/{code}/fundamentals`
*   **内容**: 机构评级、业绩预告。
*   **响应**: `{"code": "...", "data": {"analyst_ranks": [], "forecasts": []}}`

### 6.2 财务 (Financials)
*   **路径**: `/api/v1/stocks/{code}/financials`
*   **内容**: 核心利润表数据、ROE/毛利率等衍生指标。
*   **参数**: `limit` (默认 4，即最近 4 期报告)。

### 6.3 股东 (Shareholders)
*   **路径**: `/api/v1/stocks/{code}/shareholders`
*   **内容**: 股东户数历史、最新一期前十大股东。

### 6.4 资金 (Funds)
*   **路径**: `/api/v1/stocks/{code}/funds`
*   **内容**: 北向资金持股变动、历史龙虎榜记录。

### 6.5 分红 (Dividends)
*   **路径**: `/api/v1/stocks/{code}/dividends`
*   **状态**: ⚠️ **数据不足**
*   **备注**: 该接口目前返回空列表，待分红配送数据入库后开放。

### 6.6 市场纵览 (Market Overview)

#### 1. 全市场全景 (L1 Latest)
*   **路径**: `/api/v1/market/overview/latest`
*   **描述**: 返回最新交易日的全市场核心指标。
*   **响应结构**:
    *   `trade_date`: 交易日期
    *   `indices`: 核心指数表现（上证、深成、创业、科创、中证全指、沪深300等），包含 `close` 和 `pct`。
    *   `liquidity`: 成交量能（总成交额、MA5/MA20 比较、年度分位等）。
    *   `sentiment`: 情绪指标（涨跌家数、涨跌停数、连板高度、市场广度、当前市场阶段等）。

#### 2. 市场全景历史 (L1 History)
*   **路径**: `/api/v1/market/overview/history`
*   **参数**: `limit` (默认 20，最大 100)。
*   **描述**: 返回按日期倒序的市场指标列表。

#### 3. 结构分化与行业旋转 (L2 Structural)
*   **路径**: `/api/v1/market/structural/latest`
*   **描述**: 返回最新的行业旋转、风格分化及热门概念分析 (Chapter 2 核心)。
*   **响应结构**:
    *   `trade_date`: 交易日期
    *   `industry`: 
        *   `top`: 表现最强的 5 个行业。
        *   `bottom`: 表现最弱的 5 个行业。
    *   `style`: 风格指数表现（包含价值/成长、大盘/小盘等维度）。
    *   `concept`: 最活跃的前 10 个概念板块。
    *   `summary`: 自动生成的结构化分析摘要文案。

### 6.7 交易日历 (Trade Calendar)

#### 1. 交易日列表 (Trading Days)
*   **路径**: `/api/v1/calendar/trading_days`
*   **参数**: 
    *   `start_date` (optional): 开始日期 (YYYY-MM-DD)
    *   `end_date` (optional): 结束日期 (YYYY-MM-DD)
*   **描述**: 获取指定范围内的所有交易日列表。

#### 2. 是否开市 (Is Open)
*   **路径**: `/api/v1/calendar/is_open`
*   **参数**: `date` (optional): 检查日期，默认为今日。
*   **描述**: 检查特定日期是否为交易日。
*   **响应**: `{"date": "2026-04-29", "is_open": true, "status": "success"}`

#### 3. 最近交易日 (Recent)
*   **路径**: `/api/v1/calendar/recent`
*   **参数**: `limit` (默认 5): 获取最近几个交易日。
*   **描述**: 获取当前日期之前的最近 N 个交易日。

## 7. 认证与用户接口

以下接口涉及身份验证。除登录接口外，其余接口均需在 Header 中携带 `Authorization: Bearer <Token>`。

### 7.1 微信静默登录 (Auth Login)
*   **路径**: `/api/v1/auth/login`
*   **方法**: `POST`
*   **描述**: 实现微信小程序无感静默登录，建立用户身份关联并发放 JWT 凭证。
*   **请求参数**:
    ```json
    { "code": "微信 wx.login 获取的临时凭证" }
    ```
*   **响应示例**:
    ```json
    {
      "code": 200,
      "data": {
        "token": "eyJhbGciOiJIUzI1Ni...",
        "user_info": {
          "id": 1,
          "nickname": "小散张三",
          "level": 0,
          "prefs": { "ui": { "theme": "standard" } }
        }
      },
      "message": "登录成功"
    }
    ```

### 7.2 用户资料 (User Profile)
*   **路径**: `/api/v1/user/profile`
*   **方法**: `GET` / `PUT`
*   **描述**: 获取或更新用户个人资料及个性化配置。
*   **更新参数 (PUT)**: 支持 `nickname`, `avatar_url`, `gender`, `region`, `prefs` (JSON 对象)。

## 8. 股市日记接口 (Stock Diary)

全功能日记管理接口，支持 Markdown 格式与个股/标签关联。

### 8.1 日记列表 (List)
*   **路径**: `/api/v1/diaries`
*   **方法**: `GET`
*   **查询参数**:
    *   `page`: 页码 (默认 1)
    *   `size`: 每页条数 (默认 20)
    *   `tag`: 按标签名称筛选
    *   `entry_type`: 按类型筛选 (1=盘前, 2=盘中, 3=盘后, 4=周复盘, 5=随笔, 6=个股研究)
    *   `search`: 全文检索关键词 (命中标题或正文)
*   **响应**: `{"items": [...], "total": 100, "page": 1, "size": 20}`

### 8.2 日记操作 (CRUD)
*   **获取详情**: `GET /api/v1/diaries/{id}`
*   **创建日记**: `POST /api/v1/diaries`
    *   Payload: `entry_date`, `entry_type`, `title`, `content`, `stocks` (ts_code 列表), `tags` (标签名列表)。
*   **更新日记**: `PUT /api/v1/diaries/{id}`
*   **删除日记**: `DELETE /api/v1/diaries/{id}` (软删除)

## 9. 微信小程序调用示例

建议在小程序中使用 `wx.cloud.callContainer` 进行调用，这样可以免去鉴权逻辑并享受腾讯云内网加速。

```javascript
// 示例：获取茅台 K 线数据
wx.cloud.callContainer({
  "config": {
    "env": "prod-xxxxx" // 你的云托管环境ID
  },
  "path": "/api/v1/stocks/600519.SH/kline",
  "header": {
    "X-WX-SERVICE": "wxch-gateway" // 目标服务名称
  },
  "method": "GET",
  "data": {
    "limit": 10
  },
  "success": (res) => {
    console.log("K线数据:", res.data);
    // 处理返回的 data 数组渲染图表
  },
  "fail": (err) => {
    console.error("请求失败:", err);
  }
});
```

## 10. 错误处理规范

接口采用标准 HTTP 状态码：
*   **400**: 参数错误（如代码格式不支持）。
*   **401**: 认证失败（Token 过期或无效）。
*   **404**: 未找到对应股票数据。
*   **500**: 服务器内部错误。

错误响应格式如下：
```json
{
  "detail": {
    "error": {
      "code": "QUOTE_NOT_FOUND",
      "message": "未找到股票 000001.SZ 的实时数据",
      "request_id": "a1b2c3d4"
    }
  }
}
```

所有返回的 Header 中包含 `X-Request-ID`，如遇问题请提供该 ID 供后端排查日志。

## 11. 注意事项
1.  **代码标准化**: 接口已内置标准化逻辑，前端可放心传入 `600519.SH`、`sh.600519` 或纯数字 `600519`。
2.  **频率限制**: 实时行情数据通过腾讯行情源拉取，建议小程序轮询间隔不小于 **3 秒**，避免触发上游限流导致数据异常。
3.  **时区**: 所有日期数据均以 `Asia/Shanghai` 时区为准。
4.  **非交易时段**: 盘前和盘后，实时行情接口仍可请求，但所返回的五档数据和成交量将反映最后一个交易日的收盘数据。
