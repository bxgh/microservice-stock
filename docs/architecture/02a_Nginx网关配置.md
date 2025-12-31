# 02a. Nginx 网关配置 (Gateway Spec)

> **部署位置**: 腾讯云轻量服务器
> **职责**: SSL终结、流量路由、静态资源、安全防护

## 1. 核心职责边界

Nginx 是系统唯一暴露给公网的入口，其职责严格限定为：
1.  **SSL/TLS 终结**: 接收 HTTPS 请求，解密后以 HTTP 转发给后端。
2.  **请求路由**: 根据 URL Path 分发到不同的后端服务。
3.  **静态资源托管**: 前端 SPA (React) 的 HTML/JS/CSS。
4.  **基础安全**: 限流、CORS、防爬虫。

---

## 2. 完整 `nginx.conf` 配置

```nginx
worker_processes auto;

events {
    worker_connections 1024;
    use epoll;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    # ==================== 性能优化 ====================
    sendfile        on;
    tcp_nopush      on;
    keepalive_timeout  65;

    # Gzip 压缩 (JSON 数据压缩率可达 90%)
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 1k;

    # ==================== 日志格式 (含 Request ID) ====================
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$request_id"';
    access_log /var/log/nginx/access.log main;

    # ==================== 上游服务定义 ====================
    upstream cloud_api {
        server cloud-api:8000;
        keepalive 32;  # 长连接池，减少 TCP 握手开销
    }

    # ==================== HTTP -> HTTPS 重定向 ====================
    server {
        listen 80;
        server_name api.your-stock-domain.com;
        return 301 https://$host$request_uri;
    }

    # ==================== 主服务块 (HTTPS) ====================
    server {
        listen 443 ssl http2;
        server_name api.your-stock-domain.com;

        # SSL 证书 (Let's Encrypt / 腾讯云免费证书)
        ssl_certificate     /etc/nginx/certs/fullchain.pem;
        ssl_certificate_key /etc/nginx/certs/privkey.pem;
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5;
        ssl_session_cache   shared:SSL:10m;

        # -------------------- 路由规则 --------------------
        
        # 1. 静态前端资源 (React SPA)
        location / {
            root /usr/share/nginx/html;
            try_files $uri /index.html;
            expires 1d;
            add_header Cache-Control "public, immutable";
        }

        # 2. API 聚合接口 (转发到 Cloud-API)
        location /api/ {
            proxy_pass http://cloud_api;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $request_id;  # 链路追踪
            
            # 超时设置 (防止慢查询拖死网关)
            proxy_connect_timeout 5s;
            proxy_read_timeout 30s;
            proxy_send_timeout 30s;
        }

        # 3. 健康检查 (供 Docker/K8s 探活)
        location /health {
            access_log off;
            return 200 "OK";
            add_header Content-Type text/plain;
        }
    }
}
```

---

## 3. 安全加固配置

### 3.1 基础限流 (防 DDoS)
```nginx
# 在 http {} 块内添加
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# 在 location /api/ 内添加
limit_req zone=api_limit burst=20 nodelay;
```

### 3.2 CORS 配置 (小程序/Web跨域)
```nginx
# 在 location /api/ 内添加
add_header 'Access-Control-Allow-Origin' 'https://your-mini-program.domain' always;
add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;

if ($request_method = 'OPTIONS') {
    return 204;
}
```

---

## 4. Docker 部署片段

```yaml
# docker-compose.cloud.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
      - ./dist:/usr/share/nginx/html:ro
    depends_on:
      - cloud-api
    deploy:
      resources:
        limits:
          memory: 128M
```
