# 架构文档：定时任务调度与同步管线 (2.0)

## 1. 概述
本系统实现了一套高可靠、可监控的股票数据自动化同步体系。核心不再仅仅依赖单点任务，而是升级为**基于流水线 (Pipeline) 的协同调度模式**。系统以 `BaoStock API` 为调度中枢，协调 K线数据、复权因子等核心资产的每日更新。

## 2. 调度与流水线 (Scheduler & Pipeline)
### 2.1 时间配置
任务调度严格遵循 **T+0/T+1** 交易原则，目前定为每日 **17:00** 启动（闭市后）。

- **Trigger**: `cron[hour='17', minute='00']`
- **Config**: 支持通过 `app/scheduler/config.py` 或环境变量 `DAILY_SYNC_HOUR` 动态调整。

### 2.2 流水线逻辑
不再并行散乱执行，而是采用**串行流水线**模式，确保数据依赖关系的正确性：
1.  **Stage 1: A股全市场K线同步** (Daily K-Line Sync)
    *   并发度: 进程池 (ProcessPool) + 协程
    *   容错: 自动检测断点，支持从中断处恢复 (Resume capability)
2.  **Stage 2: 复权因子同步** (Adjust Factor Sync)
    *   前置条件: K线同步完成
    *   说明: 必须在K线落地后执行，以确保复权计算的基准数据完整。
3.  **Stage 3: 质量监测与上报** (Quality Assurance)
    *   动作: 计算当日同步覆盖率，写入监控数据库。

## 3. 并发与锁机制 (Concurrency & Locking)
为了平衡**高性能抓取**与**连接稳定性**，系统实施了精细化的锁策略：

- **连接建立 (Critical Section)**: 
  - 核心痛点: BaoStock 的登录/连接动作不是线程安全的。
  - 解决方案: 使用 `async with self.lock` 严格保护 `_ensure_connection()` 方法。任何时刻只有一个协程能执行连接检查或重连操作。
- **数据抓取 (Parallel Section)**:
  - 核心优化: 数据下载过程 (IO密集/耗时) **不加锁**。
  - 实现: 连接建立后，立即释放锁，允许 ProcessPool 中的 Worker 并发执行数据拉取。

## 4. 监控体系 (Monitoring System)
系统引入了独立的监控数据库 `monitoring`，不再盲目依赖日志。

### 4.1 数据模型
- **Table**: `data_sync_monitor`
- **Fields**:
  - `task_name`: 任务类型 (如 `kline_daily`)
  - `expected_count`: 预期同步数量 (全市场 A 股总数)
  - `actual_count`: 实际数据库入库数量
  - `completeness`: 完整度百分比 (例如 99.93%)
  - `status`: 状态 (SUCCESS/FAILED/INCOMPLETE)
  - `duration_ms`: 耗时统计

### 4.2 质量门禁
- 每次同步完成后，自动计算完整度。
- 若 `Completeness < 95%`，系统会自动告警 (日志层面 WARN，未来可对接钉钉/企微)。

## 5. 运维指南
- **手动触发**: 支持通过 `/api/v1/sync/run_pipeline` 立即运行全量流水线。
- **断点续传**: 若任务意外中断（如容器重启），重启后会自动读取 `sync_progress` 表，从上次中断的索引位置继续执行，无需从头开始。
- **健康检查**: 访问 `/health` 接口可确认调度器存活状态。

---
*Last Updated: 2026-01-06 (Refined for v2.0 Architecture)*
