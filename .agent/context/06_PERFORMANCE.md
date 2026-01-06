# 性能与监控指标

> **用途**: AI 评估性能与监控数据

## 性能基线

### 同步任务耗时

| 任务 | 股票数 | 平均耗时 |
|------|--------|----------|
| 全市场 K 线增量 | ~5468 | 15-25 分钟 |
| 全市场复权因子 | ~5468 | 8-12 分钟 |
| 完整性校验 | ~5468 | < 30 秒 |

### API 响应时间 (P95)

| 端点类型 | 响应时间 |
|----------|----------|
| 健康检查 | < 50ms |
| 单股 K 线 | < 500ms |
| 财务数据 | 1-3s |
| 问财选股 | 3-8s |

### 资源限制

| 服务 | 内存限制 | CPU 限制 | 内存峰值 |
|------|----------|----------|----------|
| baostock-api | 128MB | 0.5 核 | ~100MB |
| akshare-api | 128MB | 0.5 核 | ~60MB |
| pywencai-api | 128MB | 0.5 核 | ~50MB |
| stock-manager | 128MB | 0.5 核 | ~30MB |

---

## 监控体系

### 监控表

```sql
-- monitoring.data_sync_monitor
CREATE TABLE data_sync_monitor (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_name VARCHAR(50),
    sync_date DATE,
    expected_count INT,
    actual_count INT,
    completeness DECIMAL(5,2),
    status ENUM('SUCCESS', 'INCOMPLETE', 'FAILED'),
    duration_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 质量门禁

| 指标 | 阈值 | 级别 |
|------|------|------|
| 日同步完整度 | < 95% | P0 告警 |
| 日同步完整度 | 95-99% | P1 警告 |
| 同步耗时 | > 60 分钟 | P1 警告 |
| 连续失败 | ≥ 3 次 | P0 告警 |

### 监控查询

```bash
# 查询完整度趋势
curl "http://localhost:8001/api/v1/sync/verify/weekly"

# 查询时效性
curl "http://localhost:8001/api/v1/sync/freshness"
```
