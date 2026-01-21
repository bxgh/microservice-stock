---
name: MySQL to API (Complete Lifecycle)
description: 自动化从 MySQL 表或 SQL 语句创建 FastAPI 接口的完整流程。包含架构检查、代码生成、自动化测试、质量控制 (QC)、故障修复及文档化。
---

# MySQL to API 完整开发生命周期

本 Skill 指导 Agent 完成从数据库到 API 端点的全流程自动化开发，确保代码符合项目标准且经过充分验证。

## 前置条件
- 工作目录位于 `stock-manager-api` 或具备数据库访问能力的 FastAPI 服务目录。
- `.env` 文件已配置正确的数据库连接信息。
- `.agent/skills/mysql_to_api/scripts/inspect_db.py` 脚本存在。

## 工作流步骤

### 1. 需求收集 (Requirements Gathering)
明确以下信息：
- **数据源**: 表名 (Table Name) 或 SQL 查询语句。
- **实体名称**: 用于类名、文件名（如 `UserLog` -> `user_log`）。
- **API 描述**: 简述接口用途。

### 2. 数据库架构检查 (Inspect Schema)
运行检查脚本获取 JSON 格式的架构信息。
```bash
.venv/bin/python3 .agent/skills/mysql_to_api/scripts/inspect_db.py --table <TABLE_NAME>
# 或
.venv/bin/python3 .agent/skills/mysql_to_api/scripts/inspect_db.py --sql "<SQL_QUERY>"
```

### 3. 代码生成 (Code Generation)
根据架构信息生成以下文件：

#### A. 数据模型 (`app/models/<entity_name>.py`)
- 使用 `Pydantic v2` (`BaseModel`)。
- 严谨映射 MySQL 类型至 Python 类型。
- 定义 `Response` 模型，必要时定义 `Request` 模型。

#### B. 服务层 (`app/services/<entity_name>_service.py`)
- 继承项目现有的异步数据库模式 (`app.utils.database.db`)。
- 实现标准方法：`get_list` (支持分页/过滤), `get_by_id`, `create` (按需)。
- 必须包含日志记录 (`get_logger`)。
- 异常处理：捕获数据库异常 -> 记录日志 -> 抛出适当的业务异常。

#### C. API 路由 (`app/api/<entity_name>.py`)
- 定义 `APIRouter`。
- 注入 Service 依赖。
- 遵循 RESTful 规范：`GET /`, `GET /{id}` 等。
- 包含标准错误响应处理。

### 4. 路由集成 (Integration)
在 `app/main.py` 中注册新路由。
```python
from app.api import <entity_name>
# ...
app.include_router(<entity_name>.router, prefix="/api/v1/<url_path>", tags=["<Tag>"])
```

### 5. 强制质量控制与测试 (Mandatory QC & Testing)
开发完成后**必须**执行以下检查：
1. **静态检查 (Linting)**: 运行 `flake8` 或相关工具（如项目中可用）。若无工具，Agent 需人工审阅代码是否符合 PEP8。
2. **健康检查**: 确保服务能正常启动 (`GET /health`)。
3. **功能验证**: 创建测试脚本 `scripts/test_<entity_name>.py`。
   - 使用 `httpx` 调用新接口。
   - 验证 `200 OK` 状态码。
   - 验证返回的数据结构与字段准确性。

### 6. 故障修复循环 (Debug & Repair Loop)
若测试失败或 QC 发现问题，执行以下循环：
1. **分析错误**: 查看 API 响应、容器日志或测试输出。
2. **定位根因**: 检查 SQL 语法、Pydantic 模型映射或服务逻辑。
3. **修复代码**: 修改问题文件。
4. **重新测试**: 回到第 5 步，直到所有测试通过。

### 7. 文档化与提交 (Documentation & Git)
1. **接口文档**: 创建 `docs/api/<entity_name>.md` (中文)，包含 URL、请求参数、返回示例及错误码。
2. **Git 提交**: 使用符合规范的提交记录（中文）。
   - 格式: `feat: 完成 <entity_name> API 接口开发及测试`

## 质量控制标准 (QC Standards)
- **Async Only**: 所有 IO 必须异步。
- **Error Format**: 错误响应必须包含 `request_id`。
- **Logging**: 关键步骤必须记录 JSON 格式日志。
- **No Placeholders**: 禁止使用占位符，所有字段必须真实映射。
