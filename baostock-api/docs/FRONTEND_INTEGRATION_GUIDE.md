# 股票数据系统：前端集成指南 (V1.1)

本指南用于指导前端开发人员（特别是微信小程序/Vite RN 项目）对接微服务系统。

## 1. 基础访问信息

### 1.1 服务地址 (HTTPS)
系统通过 Nginx 进行了统一的反向代理，所有外部请求必须使用 **HTTPS**。

| 业务分类 | 微信端调用路径 (Base URL) | 后端容器 | 端口 |
| :--- | :--- | :--- | :--- |
| **BaoStock API** | `https://wxalwaysup.online/api/v1/baostock/` | baostock-api | 8001 |
| **AkShare API** | `https://wxalwaysup.online/api/v1/akshare/` | akshare-api | 8003 |
| **PyWencai API** | `https://wxalwaysup.online/api/v1/wencai/` | pywencai-api | 8002 |

> [!NOTE]
> 浏览器直接打开 Base URL 会返回 404，请访问具体接口（如 `/health`）。

### 1.2 跨域 (CORS) 与预检
- **CORS**: 服务端已启用 `Access-Control-Allow-Origin: *`。
- **OPTIONS**: Nginx 已配置处理 OPTIONS 预检请求（直接返回 204），适配微信工具及复杂请求。

---

## 2. 核心接口示例

### 2.1 基础连通性测试 (Health)
用于验证 Nginx 到容器的链路是否畅通。
- **GET** `.../api/v1/baostock/health`
- **GET** `.../api/v1/akshare/health`
- **响应**: `{"status": "healthy"}`

### 2.2 K 线数据接口 (BaoStock)
- **GET** `/api/v1/baostock/history/kline/{code}`
- **参数**:
  - `frequency`: d (日线), w (周线), m (月线)
  - `adjust`: 2 (前复权), 1 (后复权), 3 (不复权)
- **示例**: `https://wxalwaysup.online/api/v1/baostock/history/kline/sh.600000?frequency=d&adjust=2`

### 2.3 跨容器任务管理 (Aggregated Jobs)
系统支持通过 BaoStock 网关一站式管理所有容器的任务。设计图中的“定时任务管理”页应优先对接以下接口：

- **获取全系统任务**: `GET .../api/v1/baostock/scheduler/jobs`
  - 返回所有容器（BaoStock, AkShare, PyWencai）的任务列表。
  - 每个任务包含 `container` 字段，标识其所属容器。
- **任务控制 (运行/暂停/恢复)**: 
  - **POST** `.../api/v1/baostock/scheduler/jobs/{job_id}/{action}?container={container_name}`
  - `action`: 取值为 `run` (立即执行一次), `pause` (暂停), `resume` (恢复)。
  - `container`: 必须指定目标容器名称（如 `akshare-api`）。

### 2.4 数据同步质量核验 (Data Audit)
用于在 UI 中展示“今日下载总量”及“系统健康度”。
- **GET** `.../api/v1/baostock/sync/verify/daily?date=YYYY-MM-DD`
- **响应示例**:
```json
{
  "date": "2025-12-27",
  "actual_count": 0,
  "expected_count": 5465,
  "completeness_pct": 0.0,
  "status": "no_data_yet"
}
```
> [!TIP]
> 逻辑：对比数据库中已入库的股票数与当日 A 股市场实际存量，自动识别缺失情况。

---

## 3. 微信开发者工具配置 (关键)

> [!IMPORTANT]
> 微信开发环境对网络环境要求严格，请务必进行以下设置：

1. **证书校验**: 在开发者工具“详情” -> “本地设置”中，勾选 **“不校验合法域名、web-view（业务域名）、TLS版本以及HTTPS证书”**。
2. **合法域名**: 如果是在生产环境运行，请在[微信公众平台](https://mp.weixin.qq.com)配置如下合法域名：
   - `request合法域名`: `https://wxalwaysup.online`
3. **调用代码示例**:
```javascript
wx.request({
  url: 'https://wxalwaysup.online/api/v1/baostock/history/kline/sh.600000',
  method: 'GET',
  success: (res) => console.log(res.data)
});
```

---

## 4. 故障排查
- **405 Method Not Allowed**: 说明路径正确但方法错误（或 Nginx 锁定了该路径的 Method）。
- **404 Not Found**: 请检查 URL 是否漏掉了末尾的斜杠，或路径拼接错误。
- **Provisional headers are shown**: 检查是否勾选了“不校验域名”，或服务端 HTTPS 证书是否过期。
