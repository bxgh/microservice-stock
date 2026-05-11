# 实施计划 - E6-S1: 任务触发模式切换 (Task Trigger Mode Switch)

## 需求解析
本 Story 负责从基于时间的 Cron 调度切换到基于事件的 `WorkflowManager` 调度。具体包括：移除 `app/main.py` 中的冗余定时任务（综述、校验、审计），并建立保底 Cron 机制以确保在信号丢失的极端情况下流水线仍能完成。

## 依赖认证
- [x] `WorkflowManager` (E5-S1) 已实施并验证。
- [x] `readiness_prober_job` 已集成 Workflow 触发逻辑。

## TBD 销账
- **保底逻辑**: `safety_workflow_scan_job` 将调用 `WorkflowService.process_event`，它会从数据库查询当日所有 `READY` 状态的表并尝试驱动流水线。

## 架构溯源与风险认证
- **风险**: 如果事件信号因某种原因丢失，流水线可能中断。
- **保障**: 
    - 保底 Cron 设在 23:00，此时大部分数据均应就绪。
    - 幂等性保障：`WorkflowService` 内部已检查 `is_stage_success`，保底 Cron 不会重复跑已成功的阶段。

## 拟议变更

### [Component: stock-manager-api]

#### [MODIFY] [main.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/main.py)
- 移除以下冗余 Job 注册：
    - `daily_market_overview_sync` (19:00)
    - `daily_business_rule_check` (20:00)
    - `daily_audit` (23:30)
- 注册新 Job：
    - `safety_workflow_scan` (23:00)

#### [MODIFY] [system_jobs.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/scheduler/system_jobs.py)
- 增加 `safety_workflow_scan_job`：
    - 查询 `meta_data_readiness` 表中当日状态为 `READY` 的所有表名。
    - 调用 `workflow_service.process_event(biz_date, ready_tables)`。

#### [MODIFY] [workflow_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/workflow_service.py)
- 优化日志输出，增加阶段开始、成功、失败的结构化日志，方便监控。

## 验证计划

### 自动化测试
- Given: `meta_data_readiness` 中已有 READY 数据，但 `pipeline_run` 中无成功记录。
- When: 执行 `safety_workflow_scan_job`。
- Then: 观察流水线是否被自动激活并顺序执行。

### 手动验证
- 启动服务，通过日志确认调度器任务清单已更新。
