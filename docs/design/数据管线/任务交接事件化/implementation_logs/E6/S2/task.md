- [x] **核心逻辑开发 (WorkflowService)**
    - [x] 扩展 `WorkflowService` 定义 `PIPELINE_MORNING` 和 `PIPELINE_MAINTENANCE`
    - [x] 实现 `execute_morning_pipeline` 顺序逻辑
    - [x] 实现 `execute_maintenance_pipeline` 错峰逻辑

- [x] **任务重构 (Jobs & Probers)**
    - [x] 重构 `readiness_prober_job` 支持晨间 Canary 探测
    - [x] 将基金同步 `daily_fund_sync` 整合进盘后流水线

- [x] **系统集成 (Main Entry)**
    - [x] 更新 `app/main.py` 的调度器配置
    - [x] 清理冗余的 Cron 任务

- [x] **运维增强 (Ops API)**
    - [x] 实现 `GET /api/v1/ops/mission-control` 接口

- [x] **质量保障 (QA)**
    - [x] 模拟晨间触发验证
    - [x] 模拟深夜触发验证
    - [x] 数据库 Schema 补全审计
