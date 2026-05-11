# Walkthrough - E6-S1: 任务触发模式切换 (Task Trigger Mode Switch)

## 完成内容
完成了从基于时间的 Cron 调度向基于事件的 `WorkflowManager` 调度的全面切换，并建立了系统保底机制。

### 核心变更
1.  **[main.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/main.py)**: 移除了 `daily_market_overview_sync`, `daily_business_rule_check`, `daily_audit` 三个冗余定时任务。注册了新的 `safety_workflow_scan` 任务（每晚 23:00 执行）。
2.  **[system_jobs.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/scheduler/system_jobs.py)**: 实现了 `safety_workflow_scan_job`，它会扫描当日所有就绪数据并强制触发流水线，确保在极端情况下系统仍能自动完成任务。
3.  **[workflow_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/workflow_service.py)**: 优化了执行日志，增加了阶段开始与结束的结构化 Context 信息，提升了可监控性。

## 验证结果
- **语法检查**: `app/main.py` 与 `system_jobs.py` 编译通过。
- **逻辑验证**: 
    - [x] 确认冗余 Cron 已从注册清单中移除。
    - [x] 验证了保底扫描任务能够正确识别就绪表并调用 Workflow 服务。
    - [x] 结构化日志已生效，可在 Kibana/Grafana 中通过 `extra` 字段进行检索。

## 架构演进
至此，云端数据管线已完成“事件化”改造。
- **采集层**: 独立运行，更新 `data_readiness`。
- **编排层**: 实时监控 `data_readiness`，自动接力后续任务。
- **保底层**: 23:00 强制扫描，消除长尾时延风险。
