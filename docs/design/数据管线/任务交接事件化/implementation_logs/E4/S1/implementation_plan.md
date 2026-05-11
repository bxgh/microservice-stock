# 实施计划 - E4-S1-T2: 封装任务状态查询与监控接口

## 目标
在 `stock-manager-api` 中实现对 `meta_pipeline_run` 表的查询接口，支持全局任务执行状态的监控与可视化分析。

## 提议的变更

### [Component: stock-manager-api]

#### [NEW] [pipeline_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/pipeline_service.py)
实现任务状态机查询的核心逻辑。
- `get_pipeline_runs`: 根据 pipeline_id, biz_date, status 进行筛选查询。
- `get_latest_runs`: 获取最近执行的任务记录。
- `get_daily_stats`: 按日统计任务成功/失败比例。

#### [NEW] [pipelines.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/api/pipelines.py)
定义 FastAPI 路由。
- `GET /api/v1/pipelines/runs`: 列表查询。
- `GET /api/v1/pipelines/stats`: 统计简报。

#### [MODIFY] [main.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/main.py)
注册新的 `pipelines` 路由模块。

## 验证计划

### 自动化测试
- 编写测试脚本，调用新 API 验证返回数据格式。
- 模拟 `meta_pipeline_run` 记录并验证查询结果的准确性。

### 手动验证
- 通过 Swagger UI (`/docs`) 手动调用接口进行功能验证。
