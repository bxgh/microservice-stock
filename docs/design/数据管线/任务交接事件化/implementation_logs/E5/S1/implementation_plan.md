# 实施计划 - E5-S1: 云端四阶段流水线管理器 (WorkflowManager)

## 需求解析
本 Story 实现一个事件驱动的任务编排器 `WorkflowManager`，将原本依赖 Cron 硬编码时间的云端盘后任务（基础采集、核心综述、质量审计、跨网接力）整合为流水线。通过 `WorkflowWatcher` 探测数据就绪状态并自动触发后续阶段，降低时延并提高稳定性。

## 依赖认证
- [x] 表 `data_readiness` (legacy `meta_data_readiness`) 已存在且包含 `status` 字段。
- [x] 表 `pipeline_run` (legacy `meta_pipeline_run`) 已存在，用于追踪任务状态。
- [x] 表 `task_commands` 已存在，用于下发跨网指令。
- [x] 核心 Job (`daily_market_overview_sync_job`, `daily_business_rule_check_job`, `daily_audit_job`) 已在 `app/scheduler/` 中定义。

## TBD 销账
- **阶段定义**: 
    - `STAGE_B_SYNTHESIS`: 触发 `daily_market_overview_sync_job`。
    - `STAGE_C_QA_AUDIT`: 触发 `daily_business_rule_check_job` 和 `daily_audit_job`。
    - `STAGE_D_HANDOVER`: 触发 `TaskCommandService.create_command`。
- **触发条件**:
    - STAGE_B 触发条件: `stock_kline_daily` 且 `ods_sw_index_daily` 就绪。
    - STAGE_C 触发条件: `ads_l1_market_overview` 且 `ads_l2_industry_daily` 就绪。
    - STAGE_D 触发条件: STAGE_C 审计成功。

## 架构溯源与风险认证
- **架构模式**: 观察者模式 + 状态机。`readiness_prober_job` 作为观察者，发现状态变化后调用 `WorkflowManager`。
- **保障机制**: 
    - 状态持久化：每个阶段在 `pipeline_run` 中记录。
    - 幂等性：同一天同一阶段成功后不再触发。
    - 隔离性：Workflow 运行在异步 Task 中，不阻塞 Prober。

## 拟议变更

### [Component: stock-manager-api]

#### [MODIFY] [pipeline_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/pipeline_service.py)
- 增加 `create_run(pipeline_id, biz_date, task_id)`。
- 增加 `update_run(run_id, status, error_msg, output_summary)`。
- 增加 `is_stage_success(pipeline_id, biz_date, task_id)` 用于幂等检查。

#### [NEW] [workflow_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/workflow_service.py)
- 实现 `WorkflowService` 类。
- `process_event(biz_date, ready_tables)`: 根据就绪表清单判断触发哪个阶段。
- `execute_stage(stage_name, biz_date)`: 具体执行 Job 的逻辑，包含状态记录。

#### [MODIFY] [system_jobs.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/scheduler/system_jobs.py)
- 在 `readiness_prober_job` 循环结束后，获取当前就绪表清单，调用 `workflow_service.process_event`。

## 验证计划

### 自动化测试 (Given-When-Then)
- **AC 1 验证**: 
    - Given: `data_readiness` 中 `stock_kline_daily` 等标记为 READY。
    - When: 执行 `readiness_prober_job`。
    - Then: `WorkflowManager` 触发 `daily_market_overview_sync_job` (STAGE_B)。
- **AC 2 验证**:
    - Given: `daily_audit_job` 执行成功。
    - When: 触发 STAGE_D。
    - Then: `task_commands` 出现 PENDING 指令。

### 手动验证
- 查看 `pipeline_run` 表确认各阶段执行顺序。
