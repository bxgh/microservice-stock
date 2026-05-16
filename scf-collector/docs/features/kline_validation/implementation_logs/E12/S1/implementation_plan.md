# Implementation Plan - E12-S1: 全量数据像素级对账方案 (修订版)

## 目标描述
针对 1991 年至今的 A 股 K 线与复权因子数据，建立一套高性能、可中断、高可见性的全量巡检体系。通过将 11,000+ 个交易日任务化，实现“日级”进度管理与“多进程”并行加速，彻底净化历史存量脏数据。

## 用户评审要求
> [!IMPORTANT]
> 本方案引入了 **日级进度表 (Checkpoint Table)** 概念，巡检不再依赖简单的 CLI 参数，而是通过数据库持久化每一个交易日的审计状态。这需要执行一次 DDL 变更。

> [!WARNING]
> 并行执行将显著增加 Tushare 积分消耗速率。建议在积分充足（>2000）或非交易时段执行。

## 待决策问题
1. **并发限制**：是否限制最大并行 Worker 数量（建议 3-5 个）？
2. **审计范围**：是否需要优先审计特定年份（如 2024 年）？

---

## 拟定变更

### 1. 基础设施 (Infrastructure)

#### [NEW] [migrations/20260516_add_audit_progress_table.sql](file:///home/ubuntu/microservice-stock/migrations/20260516_add_audit_progress_table.sql)
- 创建 `meta_audit_progress_day` 表：
  - `cal_date`: DATE (PK)
  - `audit_status`: ENUM('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')
  - `error_count`: INT (审计出的异常数)
  - `last_run`: TIMESTAMP

### 2. 巡检引擎重构 (Audit Engine Refactoring)

#### [MODIFY] [kline_integrity_checker.py](file:///home/ubuntu/microservice-stock/scf-collector/scripts/audit/kline_integrity_checker.py)
- **调度逻辑重写**：
  - 从 `meta_audit_progress_day` 中动态认领 `PENDING` 任务。
  - 支持分布式执行，利用 `SELECT ... FOR UPDATE SKIP LOCKED` 实现多进程安全。
- **三阶探测集成**：
  - 保留并优化“计数 -> 基准 -> 像素”三阶探测逻辑，作为单日审计的标准流程。

### 3. 调度工具 (Orchestrator)

#### [NEW] [scripts/audit/audit_orchestrator.py](file:///home/ubuntu/microservice-stock/scf-collector/scripts/audit/audit_orchestrator.py)
- **初始化工具**：一次性将 1991 年至今的交易日填入进度表。
- **监控面板**：实时统计全量进度的百分比、预计剩余时间 (ETA)。

---

## 验证计划

### 自动化测试
- **任务分配测试**：启动 2 个 Worker，验证是否会出现重复审计同一天的情况。
- **异常恢复测试**：在 Worker 运行时强杀，验证 `RUNNING` 状态的任务是否能正确回归或重置。

### 手动校验
- **2024 专项审计**：优先完成 2024 年的审计，对比修复前后的数据准确率。
- **报告验证**：确保 `REPORT.html` 能够实时拉取进度表中的聚合数据。
