# Stock-Manager API 部署与外网访问配置

> **服务器IP**: 124.221.80.250  
> **服务端口**: 8004  
> **更新日期**: 2026-01-01

---

## 1. 当前状态

| 组件 | 内网访问 | 外网访问 | 状态 |
|:---|:---:|:---:|:---|
| stock-manager | ✅ localhost:8004 | ⚠️ 需配置 | 待开放 |
| baostock-api | ✅ localhost:8001 | ⚠️ 需配置 | 待开放 |

---

## 2. 腾讯云防火墙配置

### 2.1 需要开放的端口

在腾讯云控制台 → 轻量应用服务器 → 防火墙规则中添加：

| 端口 | 协议 | 来源 | 说明 |
|:---|:---|:---|:---|
| 8004 | TCP | 0.0.0.0/0 | Stock-Manager API |
| 8001 | TCP | 0.0.0.0/0 | BaoStock API (可选) |
| 8003 | TCP | 0.0.0.0/0 | AkShare API (可选) |

### 2.2 命令行配置（Ubuntu UFW）

```bash
# 开放端口
sudo ufw allow 8004/tcp
sudo ufw allow 8001/tcp
sudo ufw allow 8003/tcp

# 查看状态
sudo ufw status
```

---

## 3. 前端访问地址

### 3.1 开发环境（推荐）
```
http://localhost:8004/api/v1
```
- 适用场景：前端开发人员本地调试
- 优点：无需跨域，响应快
- 缺点：仅本机可访问

### 3.2 直连公网IP（临时方案）
```
http://124.221.80.250:8004/api/v1
```
- 适用场景：演示、测试
- 优点：直接访问，配置简单
- 缺点：
  - 暴露端口，安全性低
  - 需要配置CORS
  - IP变更需要修改代码

### 3.3 Nginx网关（生产推荐）⭐
```
https://api.your-domain.com/stock-manager/api/v1
```
- 适用场景：生产环境
- 优点：
  - 统一入口，安全
  - SSL加密
  - 负载均衡
  - 日志追踪

---

## 4. CORS 配置（如使用公网IP）

如果前端直连公网IP，需要在 `stock-manager-api/app/main.py` 添加CORS支持：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 5. 推荐部署方案

### 方案A：前端同服务器部署（最简单）

```
前端页面 → localhost:8004 (内网访问)
```
- 前端打包后放在服务器
- 通过Nginx托管静态文件
- API调用走内网，无需CORS

### 方案B：Nginx反向代理（推荐）

```nginx
# /etc/nginx/sites-available/api.conf
server {
    listen 80;
    server_name api.your-domain.com;
    
    location /stock-manager/ {
        proxy_pass http://127.0.0.1:8004/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

前端访问：`http://api.your-domain.com/stock-manager/api/v1/...`

### 方案C：直连公网IP + CORS（临时）

1. 开放防火墙端口8004
2. 添加CORS中间件
3. 前端配置：`http://124.221.80.250:8004/api/v1`

---

## 6. 前端环境配置参考

### .env.development (本地开发)
```bash
REACT_APP_API_BASE_URL=http://localhost:8004/api/v1
```

### .env.production (生产部署)

**选项1：Nginx网关**
```bash
REACT_APP_API_BASE_URL=https://api.your-domain.com/stock-manager/api/v1
```

**选项2：直连IP（临时）**
```bash
REACT_APP_API_BASE_URL=http://124.221.80.250:8004/api/v1
```

---

## 7. 快速测试命令

```bash
# 1. 内网测试
curl http://localhost:8004/health

# 2. 外网测试（需先开放防火墙）
curl http://124.221.80.250:8004/health

# 3. 测试具体接口
curl http://124.221.80.250:8004/api/v1/metadata/baseline/current
```

---

## 8. 安全建议

⚠️ **生产环境不建议直接暴露端口8004**

推荐方案：
1. ✅ 使用Nginx作为统一网关
2. ✅ 配置SSL证书（HTTPS）
3. ✅ 限制CORS来源白名单
4. ✅ 添加API限流保护

---

*配置完成后，请根据实际选择的方案更新前端 `.env` 文件*
