# 实施计划 - E6-S4: 每日任务执行总结报告 (Daily Summary Report)

## 角色激活
- **[Data Operations Engineer]**: 负责任务执行数据的汇总逻辑与报表模版设计。
- **[Reliability Engineer]**: 负责总结任务的调度注册与端到端闭环验证。

## 需求解析
在每日深夜流水线收尾阶段，自动汇总“晨间预就绪”、“盘后流水线”及“深夜维护”三个阶段的所有任务执行情况。报告需包含：各阶段成功率、异常任务清单、总执行耗时以及关键质量指标预览。

## 拟议变更

### [Component: stock-manager-api]

#### [MODIFY] [workflow_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/workflow_service.py)
- 增加 `send_daily_summary_report(biz_date: date)` 方法：
    - 调用 `ops_service.get_mission_control` 获取全天任务树。
    - 统计总任务数、成功数、失败数、总耗时。
    - 构造一个“日终总结”专用 HTML 模板：
        - 顶部展示“数据管线日终报告”大标题及总揽看板。
        - 中部按阶段展示明细表格，使用不同颜色标识任务状态（成功-绿, 失败-红, 进行中-蓝）。
        - 底部提供 Mission Control 看板的深度链接（API URL）。
    - 通过 `alerter.alert` 发送（Level 设为 INFO 或 ERROR，取决于是否有失败任务）。

#### [MODIFY] [system_jobs.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/scheduler/system_jobs.py)
- 增加 `daily_pipeline_summary_job` 任务函数：
    - 默认执行日期为 `today`。
    - 增加标准化 Docstring（目标表: `meta_pipeline_run`）。

#### [MODIFY] [main.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/main.py)
- 注册 `daily_pipeline_summary_job`：
    - 执行时间建议：23:45 (覆盖盘后与部分深夜前期任务) 或次日 05:30 (覆盖所有深夜任务)。
    - **决定**：注册为 **23:45** (初步总结) 及 **次日 06:00** (完整终结报告)。

## 验证计划

### 自动化验证 (Docker 环境)
- [ ] 运行 `test_daily_summary.py` 脚本，强行触发报告生成。
- [ ] 审计生成的 HTML 报表是否包含完整的三个 Pipeline 节点。
- [ ] 验证“失败数”统计是否准确。

### 手工核对
- [ ] 确认邮件正文的视觉排版符合“整齐、标准化”要求。
