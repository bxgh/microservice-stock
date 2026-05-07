# 实施计划 - E5-S1: 云端任务流水线编排器 (WorkflowManager)

## 目标
实现云端任务的自动化接力，确保盘后数据采集、校验、审计到跨网下发的顺序完整与执行连贯。

## 提议的变更

### [Component: stock-manager-api]

#### [NEW] [workflow_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/workflow_service.py)
实现核心编排逻辑。
- `run_stage_pipeline(biz_date, current_stage)`: 
    - **Stage B (Synthesis)**: 调用 `daily_market_overview_sync_job`。
    - **Stage C (QA/Audit)**: 顺序调用 `daily_business_rule_check_job` -> `daily_audit_job`。
    - **Stage D (Handover)**: 调用 `TaskCommandService` 下发指令。
- 状态记录：在 `meta_pipeline_run` 中记录每个阶段的执行情况。

#### [MODIFY] [system_jobs.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/scheduler/system_jobs.py)
集成触发点。
- 在 `readiness_prober_job` 探测到关键数据变化或 `ALL_READY` 时，调用 `workflow_service.run_stage_pipeline`。
- 修改 `daily_audit_job` 等函数，使其支持通过参数控制是否发送邮件告警（避免中间环节产生冗余报告）。

#### [MODIFY] [scheduler_proxy.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/scheduler_proxy.py)
- 增加对内部 Job 的直接触发能力，不依赖 Cron 时间。

## 验证计划

### 自动化测试
- 模拟 `ALL_READY` 信号。
- 观察是否能按照 **业务校验 -> 审计 -> 指令下发** 的顺序自动执行。
- 验证 `meta_pipeline_run` 中的状态流转记录。

### 手动验证
- 通过 Swagger API 手动触发 Stage B，观察后续 Stage C 和 D 是否自动接力。
