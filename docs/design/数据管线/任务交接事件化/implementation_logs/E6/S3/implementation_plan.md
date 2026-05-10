# 实施计划 - E6-S3: 告警邮件系统标准化优化

## 角色激活
- **[Infrastructure Architect]**: 负责邮件模板设计与系统配置扩展。
- **[Reliability Engineer]**: 负责装饰器增强逻辑实现及全系统任务文档字符串标准化。

## 需求解析
对现有的告警邮件系统进行美化与信息增强，确保运维人员能清晰识别执行环境（服务器名称）、操作对象（目标表）及详细描述（功能说明）。

## 拟议变更

### [Component: stock-manager-api]

#### [MODIFY] [config.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/config.py)
- 增加 `SERVER_NAME` 配置项，默认为 `Tencent Cloud - Node-Cloud`。

#### [MODIFY] [alerter.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/utils/alerter.py)
- 重构 `_send_email` 方法：
    - 切换为 HTML 格式邮件 (`MIMEText(html, "html")`)。
    - 设计 Premium 感的 HTML 模板：
        - 标题栏背景色按级别区分（INFO-蓝, ERROR-红, CRITICAL-黑）。
        - 表格化显示关键信息。
        - 显式展示执行服务器。

#### [MODIFY] [scheduler_decorators.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/common/scheduler_decorators.py)
- 增强 `notify_result` 装饰器：
    - 增加 docstring 解析逻辑，提取：
        - `任务描述` (任务标题)
        - `目标表` (Target Table)
        - `功能描述` (Function Description)
    - 将解析出的元数据合并入 `context` 传递给 `alerter.alert`。

#### [MODIFY] [jobs.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/scheduler/jobs.py)
- 对核心同步任务（如 `daily_stock_basic_sync_job`, `daily_fund_sync_job` 等）的 docstring 进行标准化重写。

## 验证计划

### 自动化验证 (Docker 环境)
- [ ] 运行测试脚本模拟任务执行。
- [ ] 观察容器日志中输出的 HTML 模板预览。
- [ ] 验证解析器是否正确从函数 docstring 提取了“目标表”字段。

### 手工核对
- [ ] 检查邮件正文是否包含正确的服务器名称。
