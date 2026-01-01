# Stock-Manager API 文档更新总结

> **更新日期**: 2026-01-01  
> **服务器IP**: 124.221.80.250  
> **服务端口**: 8004

---

## 已更新的文档

### 1. 前端API文档 ✅
**文件**: `docs/api/stock-manager-frontend-api.md`

**更新内容**:
- ✅ 开发环境: `http://localhost:8004/api/v1`
- ✅ 生产环境: `http://124.221.80.250:8004/api/v1`
- ✅ 环境变量配置示例
- ✅ Axios 客户端配置

### 2. 部署指南 ✅
**文件**: `docs/deployment/stock-manager-external-access.md`

**更新内容**:
- ✅ 服务器IP: 124.221.80.250
- ✅ 防火墙配置说明
- ✅ CORS配置指南
- ✅ 三种部署方案对比

---

## 当前访问状态

### 内网访问 ✅
```bash
curl http://localhost:8004/health
# 返回: {"status":"healthy"}
```

### 外网访问 ⚠️
```bash
curl http://124.221.80.250:8004/health
# 状态: 连接超时
# 原因: 端口8004未在防火墙开放
```

---

## 前端接入指南

### 步骤1: 创建环境配置
```typescript
// src/config.ts
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://124.221.80.250:8004/api/v1';

export const config = {
  apiBaseUrl: API_BASE_URL
};
```

### 步骤2: 配置环境变量

**开发环境** `.env.development`:
```bash
REACT_APP_API_BASE_URL=http://localhost:8004/api/v1
```

**生产环境** `.env.production`:
```bash
REACT_APP_API_BASE_URL=http://124.221.80.250:8004/api/v1
```

### 步骤3: 初始化Axios
```typescript
// src/api/client.ts
import axios from 'axios';
import { config } from '../config';

export const apiClient = axios.create({
  baseURL: config.apiBaseUrl,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});
```

### 步骤4: 使用API
```typescript
// src/api/stockManager.ts
import { apiClient } from './client';

export const stockManagerAPI = {
  getTradingDays: (week = 'current') =>
    apiClient.get('/metadata/calendar/tradingDays', { params: { week } }),
  
  getBaseline: () =>
    apiClient.get('/metadata/baseline/current'),
  
  getAuditReport: (week = 'current') =>
    apiClient.get('/audit/weekly', { params: { week } })
};
```

---

## 开放外网访问（可选）

### 方法1: 腾讯云控制台
1. 登录腾讯云控制台
2. 轻量应用服务器 → 防火墙
3. 添加规则:
   - 端口: 8004
   - 协议: TCP
   - 来源: 0.0.0.0/0

### 方法2: 命令行
```bash
sudo ufw allow 8004/tcp
sudo ufw reload
```

### 方法3: 添加CORS支持
在 `stock-manager-api/app/main.py` 添加:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应指定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 推荐方案

### 方案A: 本地开发（推荐新手）✅
```
前端: localhost:3000
后端: localhost:8004
```
- 优点: 无需配置，开箱即用
- 缺点: 只能本机访问

### 方案B: 前端部署到服务器（推荐）⭐
```
前端: 部署到腾讯云
后端: localhost:8004 (内网)
```
- 优点: 安全，无需开放端口
- 缺点: 需要构建部署流程

### 方案C: 直连公网IP（演示用）
```
前端: 任意位置
后端: 124.221.80.250:8004 (外网)
```
- 优点: 灵活，可远程访问
- 缺点: 需开放端口，安全性低

---

## 相关文档

- [前端API文档](../api/stock-manager-frontend-api.md)
- [部署指南](../deployment/stock-manager-external-access.md)
- [QC质量报告](../qc/stock-manager-api-qc-report.md)
- [服务规划文档](../architecture/02e_Stock-Manager服务规划.md)

---

*文档版本: v1.0*  
*最后更新: 2026-01-01*
