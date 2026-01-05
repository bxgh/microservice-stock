# Task-Orchestrator 核心架构理念

> **目的**: 提供一份可移植的架构设计原则，适用于任何环境部署调度系统。  
> **日期**: 2026-01-03

---

## 1. 中心化调度原则

```
┌─────────────────────────────────────────────┐
│           task-orchestrator (大脑)           │
│  • 唯一调度源，避免任务分散                   │
│  • 业务服务只暴露 HTTP/执行端点               │
│  • 全局视野，支持任务依赖编排                 │
└─────────────────────────────────────────────┘
```

**核心思想**: 所有定时任务由一个中心化的调度器管理，业务服务本身不包含调度逻辑。

---

## 2. 执行器分离（Orchestrator vs Worker）

| 组件 | 职责 | 运行模式 |
|:-----|:-----|:---------|
| **Orchestrator** | 调度、编排、监控 | 长驻服务 |
| **Worker** | 执行实际业务逻辑 | 临时容器/进程 |

> **核心理念**: 调度器不执行业务逻辑，Worker 用完即销毁。

**优势**:
- 资源按需分配，空闲时不占用
- 水平扩展简单（增加 Worker 数量）
- 隔离性好，避免 Worker 故障影响调度器

---

## 3. DAG 工作流引擎

```yaml
# 任务依赖编排
stages:
  - sync-shard-0  ─┬─►  quality-check  ─►  auto-repair
  - sync-shard-1  ─┤
  - sync-shard-2  ─┤
  - sync-shard-3  ─┘
```

**支持模式**:
- **顺序执行**: A → B → C
- **扇出/扇入 (Fan-out/Fan-in)**: A → [B1, B2, B3] → C
- **条件执行**: if A.success then B else C
- **失败策略**: Retry / Skip / Block

**状态流转**:
```
PENDING → RUNNING → SUCCESS / FAILED → RETRYING
```

---

## 4. 智能触发器

| 触发器类型 | 描述 | 用例 |
|:-----------|:-----|:-----|
| **TradingDayTrigger** | 仅交易日触发 | 股票数据同步 |
| **DataReadyTrigger** | 上游数据就绪时触发 | 依赖外部信号 |
| **CronTrigger** | 传统定时 | 日常维护 |

```python
async def should_fire(self):
    if not await calendar.is_trading_day():
        return False  # 非交易日跳过
    return True
```

**自适应触发**: 可结合历史数据预测最佳执行时间窗口。

---

## 5. 自动化边界控制

| 异常规模 | 处理策略 |
|:---------|:---------|
| < 50 条 | 自动修复 |
| 50-200 条 | 告警 + 人工确认 |
| > 200 条 | 终止 + 紧急告警 |

**设计原则**: 小问题自动处理，大问题及时上报，避免误操作放大影响。

---

## 6. 分片并行执行

```yaml
parallelism: 4
command_template: "python -m jobs.sync --shard={shard_index} --total={total_shards}"
```

**分片策略**:
- 按股票代码范围分片
- 按时间范围分片
- 动态分片（根据数据量自动调整）

**容错机制**: 单分片失败可独立重试，不影响其他分片。

---

## 7. 生命周期管理

```
启动时: 清理孤儿容器 (orphan cleanup)
运行时: 容器状态监控 + 超时控制
关闭时: 优雅终止所有 Worker
```

**孤儿容器清理**:
```python
async def cleanup_orphan_containers():
    containers = docker_client.containers.list(
        filters={"label": "managed_by=task-orchestrator"}
    )
    for c in containers:
        if is_stale(c):  # 超过阈值时间
            c.stop(timeout=30)
            c.remove()
```

---

## 8. YAML 驱动配置

```yaml
version: "1.0"
timezone: "Asia/Shanghai"

tasks:
  - id: daily_sync
    name: 每日数据同步
    schedule:
      type: trading_cron
      expression: "30 18 * * 1-5"
    target:
      image: worker:latest
      parallelism: 4
    error_handling:
      max_retries: 3
      retry_delay: 60s
      timeout: 30m
      on_failure: notify
    resource_limits:
      memory: "2G"
      cpus: "1.0"
```

**优势**: 配置可版本控制，易于审计和回滚。

---

## 9. 监控与告警

**Prometheus 指标**:
```python
task_execution_duration_seconds{workflow, task, status}
task_execution_total{workflow, task, status="success|failed"}
parallel_containers_running{workflow}
container_cleanup_failures_total
```

**告警规则**:
| 条件 | 级别 | 通道 |
|:-----|:-----|:-----|
| 任务连续失败 3 次 | WARNING | 企微群 |
| 容器清理失败 | CRITICAL | 电话/短信 |
| 队列积压 > 10 | WARNING | 邮件 |

---

## 10. 可替代技术栈

| 模块 | 本项目实现 | 可替代方案 |
|:-----|:-----------|:-----------|
| 调度引擎 | APScheduler | Celery Beat, Airflow Scheduler |
| 执行器 | Docker SDK | subprocess, Kubernetes Jobs |
| DAG 引擎 | 自研拓扑排序 | Prefect, Dagster, Airflow DAG |
| 状态存储 | MySQL + Redis | PostgreSQL, SQLite, etcd |
| 日历服务 | CalendarService | 外部交易日历 API |

---

## 总结

这套架构的核心价值在于:

1. **解耦**: 调度与执行分离
2. **弹性**: Worker 按需创建销毁
3. **可靠**: DAG 编排 + 失败重试
4. **可观测**: 完整的日志、指标、告警
5. **可配置**: YAML 驱动，易于扩展

可在任何支持容器或进程管理的环境中复制此架构。
