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
    | `frequency` | `string` | 否 | 频率：`d` (日线, 默认), `w` (周线), `m` (月线) | `w` |
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

## 3. 微信小程序调用示例

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

## 4. 错误处理规范

接口采用标准 HTTP 状态码：
*   **400**: 参数错误（如代码格式不支持）。
*   **404**: 未找到对应股票数据。
*   **500**: 服务器内部错误（详见返回内容中的 `message`）。

所有返回的 Header 中包含 `X-Request-ID`，如遇问题请提供该 ID 供后端排查日志。

## 5. 注意事项
1.  **代码标准化**: 接口已内置标准化逻辑，前端可放心传入 `600519.SH` 或 `sh.600519`。
2.  **频率限制**: 生产环境数据库连接池已配置，但请避免在 `onShow` 中进行高频无意义轮询。
3.  **时区**: 所有日期数据均以 `Asia/Shanghai` 时区为准。
