# Task-Orchestrator 实施方案 (Epics)

> **创建日期**: 2026-01-04  
> **版本**: 1.0

---

## 现有实现基线

### ✅ 已完成功能

| 功能 | 实现位置 | 状态 |
|:-----|:---------|:-----|
| APScheduler 调度引擎 | `baostock-api/app/scheduler/scheduler.py` | ✅ 生产运行中 |
| 综合同步流水线 | `baostock-api/app/scheduler/jobs.py` | ✅ K线 + 复权因子串行 |
| 任务配置管理 | `baostock-api/app/scheduler/config.py` | ✅ 环境变量支持 |
| 跨服务任务聚合 | `baostock-api/app/api/scheduler.py` | ✅ HTTP 聚合 akshare/pywencai |
| 交易日历服务 | `stock-manager-api/app/services/calendar_service.py` | ✅ `trade_cal` 表查询 |
| 任务控制 API | `/scheduler/jobs/{id}/run\|pause\|resume` | ✅ 前端可调用 |

### ⚠️ 待补充功能

| 功能 | 当前状态 | 影响 |
|:-----|:---------|:-----|
| TradingDayTrigger | ❌ 未实现 | 非交易日仍会触发任务 |
| 任务状态持久化 | ⚠️ 内存存储 | 服务重启后状态丢失 |
| DAG 依赖编排 | ❌ 未实现 | 复杂工作流需手动编排 |
| 告警通知 | ❌ 未实现 | 任务失败无主动通知 |

---

## EPIC-O01: 交易日智能触发器

### 目标
实现 `TradingDayTrigger`，使定时任务仅在交易日触发，避免非交易日浪费资源。

### 技术方案

```python
# baostock-api/app/scheduler/triggers.py

from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

class TradingDayCronTrigger(CronTrigger):
    """仅在交易日触发的 Cron 触发器"""
    
    def __init__(self, calendar_service, **kwargs):
        super().__init__(**kwargs)
        self.calendar_service = calendar_service
    
    def get_next_fire_time(self, previous_fire_time, now):
        next_time = super().get_next_fire_time(previous_fire_time, now)
        
        # 跳过非交易日
        while next_time and not self._is_trading_day(next_time):
            next_time = super().get_next_fire_time(next_time, now)
        
        return next_time
    
    def _is_trading_day(self, dt: datetime) -> bool:
        # 同步调用交易日历（APScheduler 触发器不支持 async）
        # 使用 Redis 缓存避免频繁 DB 查询
        pass
```

### 任务拆解

| 任务 | 描述 | 估时 |
|:-----|:-----|:-----|
| O01-1 | 创建 `triggers.py`，实现 `TradingDayCronTrigger` | 2h |
| O01-2 | 添加交易日缓存（Redis 或本地） | 1h |
| O01-3 | 修改 `jobs.py`，使用新触发器 | 0.5h |
| O01-4 | 测试：验证非交易日不触发 | 1h |

### 验收标准
- [ ] 非交易日（周末、节假日）不触发同步任务
- [ ] 交易日历缓存命中率 > 99%
- [ ] 不影响现有任务的正常调度

---

## EPIC-O02: 任务状态 Redis 持久化

### 目标
将任务运行状态从内存 `set()` 迁移至 Redis，实现服务重启后状态可恢复。

### 当前问题

```python
# 当前实现 (scheduler.py:44)
self._current_running_jobs = set()  # 内存存储，重启丢失
```

### 技术方案

```python
# Redis 存储结构
task:status:{task_id}  → {
    "status": "running|success|failed",
    "started_at": "2026-01-04T18:30:00",
    "finished_at": null,
    "error": null
}
task:lock:{task_name}  → {owner_id, expire_time}  # 分布式锁
```

### 任务拆解

| 任务 | 描述 | 估时 |
|:-----|:-----|:-----|
| O02-1 | 创建 `task_state.py`，封装 Redis 状态操作 | 1.5h |
| O02-2 | 修改 `scheduler.py`，替换内存存储 | 1h |
| O02-3 | 添加任务执行互斥锁（防止重复执行） | 1h |
| O02-4 | 添加启动时状态恢复逻辑 | 0.5h |
| O02-5 | 测试：模拟服务重启验证状态恢复 | 1h |

### 验收标准
- [ ] 服务重启后 `GET /scheduler/jobs` 返回正确状态
- [ ] 长时间运行任务不会因重启被误标记为 "active"
- [ ] 任务互斥锁防止并发执行

---

## EPIC-O03: YAML 驱动任务配置

### 目标
将硬编码的任务配置迁移至 YAML 文件，支持热更新和版本控制。

### 当前问题

```python
# 当前实现 (config.py)
SCHEDULER_CONFIG = {
    "jobs": {
        "daily_comprehensive_sync": {
            "hour": 18, "minute": 30, ...
        }
    }
}  # 修改需重启服务
```

### 目标配置格式

```yaml
# config/tasks/baostock-tasks.yaml
version: "1.0"
timezone: "Asia/Shanghai"

tasks:
  - id: daily_comprehensive_sync
    name: 每日综合数据同步
    schedule:
      type: trading_cron
      expression: "30 18 * * 1-5"
    target:
      type: internal
      function: jobs.daily_comprehensive_sync_job
    error_handling:
      max_retries: 3
      retry_delay: 300
```

### 任务拆解

| 任务 | 描述 | 估时 |
|:-----|:-----|:-----|
| O03-1 | 定义 YAML Schema（Pydantic 模型） | 1h |
| O03-2 | 创建 `config_loader.py`，解析 YAML | 1h |
| O03-3 | 修改 `scheduler.py`，支持配置加载 | 1.5h |
| O03-4 | 添加热更新 API `/scheduler/reload` | 1h |
| O03-5 | 迁移现有任务配置至 YAML | 0.5h |

### 验收标准
- [ ] 所有任务从 YAML 配置加载
- [ ] 修改 YAML 后调用 `/scheduler/reload` 生效
- [ ] 配置文件可纳入 Git 版本控制

---

## EPIC-O04: DAG 工作流编排 (Phase 2)

### 目标
支持多任务依赖编排，实现 `sync_kline → sync_adjust → quality_check` 流水线。

### 当前状态
已有简单串行实现 (`daily_comprehensive_sync_job`)，但不支持失败重试单步骤。

### 技术方案

```yaml
# DAG 定义示例
workflow:
  id: daily_sync_pipeline
  stages:
    - id: sync_kline
      task: daily_kline_sync
    - id: sync_adjust
      task: daily_adjust_factor_sync
      depends_on: [sync_kline]
    - id: quality_check
      task: verify_daily_data
      depends_on: [sync_kline, sync_adjust]
```

### 任务拆解

| 任务 | 描述 | 估时 |
|:-----|:-----|:-----|
| O04-1 | 设计 DAG 数据结构 | 1h |
| O04-2 | 实现拓扑排序算法 | 1.5h |
| O04-3 | 实现 DAG 执行器 | 2h |
| O04-4 | 支持单节点失败重试 | 1.5h |
| O04-5 | 集成至 YAML 配置 | 1h |

### 验收标准
- [ ] 任务按依赖顺序执行
- [ ] 单节点失败不影响已完成节点
- [ ] 支持从失败节点重新执行

---

## EPIC-O05: 告警通知集成

### 目标
任务失败时自动发送告警通知（日志 → 企微/邮件）。

### 阶段规划

| 阶段 | 通知渠道 | 实现方式 |
|:-----|:---------|:---------|
| Phase 1 | 结构化日志 | JSON 日志 + 告警标记 |
| Phase 2 | 企业微信 | Webhook 机器人 |
| Phase 3 | 邮件 | SMTP 发送 |

### 任务拆解

| 任务 | 描述 | 估时 |
|:-----|:-----|:-----|
| O05-1 | 添加告警日志格式 `level=ALERT` | 0.5h |
| O05-2 | 创建 `notifier.py` 抽象层 | 1h |
| O05-3 | 实现企微 Webhook 通知器 | 1h |
| O05-4 | 配置告警阈值（连续失败 N 次） | 0.5h |

---

## 实施优先级矩阵

```
         高价值
            ▲
            │
   O01 ◆────┼───────────────◆ O02
(交易日)    │              (状态持久化)
            │
            │       O03 ◆
            │     (YAML配置)
            │
   O05 ◆────┼───────────────◆ O04
  (告警)    │              (DAG编排)
            │
            ▼
        低价值
   低成本 ──────────────────► 高成本
```

### 推荐实施顺序

| 顺序 | Epic | 理由 |
|:-----|:-----|:-----|
| 1️⃣ | **O01** 交易日触发器 | 低成本高价值，立即减少无效执行 |
| 2️⃣ | **O02** 状态持久化 | 解决重启状态丢失的核心痛点 |
| 3️⃣ | **O03** YAML 配置 | 为后续扩展打基础 |
| 4️⃣ | **O05** 告警通知 | 提高运维可见性 |
| 5️⃣ | **O04** DAG 编排 | 复杂度高，按需实施 |

---

## 资源约束提醒

| 约束 | 限制 | 影响 |
|:-----|:-----|:-----|
| **内存** | 4GB 总量 | 新增功能不应显著增加内存占用 |
| **Redis** | 256MB | 任务状态数据需设置 TTL |
| **CPU** | 2 核 | DAG 并行度限制为 1 |

---

> **下一步**: 选择一个 Epic 开始实施，或对方案提出修改意见。
