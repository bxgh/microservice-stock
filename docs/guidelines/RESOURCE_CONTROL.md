# 资源控制部署指南

## 当前配置

### 单容器资源限制
- **CPU**: 最多 0.5 核心
- **内存**: 100MB 硬限制，50MB 预留
- **健康检查**: 每 60 秒一次（降低资源消耗）

### 总资源占用（3个服务）
- **CPU**: 最多 1.5 核心
- **内存**: 最多 300MB
- **网络**: 桥接网络共享

---

## 部署命令

### 重启服务应用新配置
```bash
cd /home/ubuntu/microservice-stock
docker compose down
docker compose up -d
```

### 验证资源限制
```bash
# 查看实时资源使用
docker stats

# 查看内存限制
docker inspect akshare-api | grep -A 5 Memory

# 查看CPU限制
docker inspect akshare-api | grep -A 5 Cpu
```

---

## 按需启动服务

如果内存不足，可以只启动需要的服务：

```bash
# 只启动 BaoStock API
docker compose up -d baostock-api

# 只启动 BaoStock + AkShare
docker compose up -d baostock-api akshare-api

# 启动全部
docker compose up -d
```

---

## 监控命令

```bash
# 持续监控
docker stats

# 查看服务状态
docker compose ps

# 查看日志（限制行数）
docker compose logs --tail=50 akshare-api
```

---

## 内存不足时的应急措施

### 1. 停止不常用的服务
```bash
# 停止 PyWencai（反爬严重，使用率低）
docker compose stop pywencai-api
```

### 2. 重启服务释放内存
```bash
docker compose restart baostock-api
```

### 3. 清理 Docker 缓存
```bash
docker system prune -f
docker image prune -a -f
```

---

## 性能调优建议

### Python 优化
在 Dockerfile 中已添加：
- `PYTHONUNBUFFERED=1` - 减少缓冲
- `PIP_NO_CACHE_DIR=1` - 不缓存pip包

### Uvicorn workers
当前每个服务 1 个 worker，如需提高性能：
```bash
# 修改 CMD 为
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```
⚠️ 注意：workers=2 会使内存翻倍

---

## 服务器总资源规划

| 服务 | CPU | 内存 | 状态 |
|------|-----|------|------|
| akshare-api | 0.5核 | 100MB | 可选 |
| baostock-api | 0.5核 | 100MB | **推荐** |
| pywencai-api | 0.5核 | 100MB | 可选 |
| **总计** | 1.5核 | 300MB | |
| **剩余** | ~2核 | ~2GB | 其他服务 |
