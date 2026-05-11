# 每日任务执行总结报告 - E6-S4

- [ ] **数据聚合层开发**
    - [ ] `WorkflowService` 增加 `send_daily_summary_report` 逻辑
    - [ ] 集成 `ops_service.get_mission_control` 数据源

- [ ] **报表模版设计**
    - [ ] 设计 HTML Summary 专用模版（统计卡片 + 阶段明细表）
    - [ ] 实现自动判定级别（存在失败任务则设为 ERROR）

- [ ] **任务注册**
    - [ ] `system_jobs.py` 增加 `daily_pipeline_summary_job`
    - [ ] `main.py` 注册每日 23:45 自动触发

- [ ] **验证与交付**
    - [ ] 容器内模拟生成测试报告
    - [ ] 物理存证存档
