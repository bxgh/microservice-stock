# Story E23-S1: 格言库建表与手工录入接口 · 实施方案

本实施方案用于指导 Epic E23 中的第一个 Story——**E23-S1** 的代码开发。本 Story 的职责是创建格言库物理表、个性化用户状态表和每日锁定状态表，并实现格言的小程序端手工录入 API，进行严格的字数拦截校验。

---

## 1. 激活角色
*   **激活角色**：`[Backend Engineer]`, `[Database Expert]`, `[QA Engineer]`

---

## 2. 需求解析 (3句话)
1. 编写包含格言主表、用户状态表、日内锁定表的 MySQL 5.7 迁移 SQL 脚本，并持久化完成建表。
2. 编写 FastAPI Pydantic 模型，设置 10-500 字的格言字数限制，以提供严格的前端录入防空与超限拦截。
3. 编写格言录入的异步 Service 层逻辑与 API 路由，支持鉴权并返回新增主键自增 ID。

---

## 3. 拟改动文件清单

*   **[NEW]** `migrations/v2.1_add_maxim_tables.sql`：MySQL 5.7 建表迁移脚本。
*   **[NEW]** `app/models/checkin.py`：Pydantic 模型定义。
*   **[NEW]** `app/services/checkin_service.py`：格言手工创建与管理 Service 逻辑。
*   **[NEW]** `app/api/checkin.py`：`POST /api/v1/checkin/maxim/quote` API 路由。
*   **[MODIFY]** `app/main.py`：注册 `/api/v1/checkin` 路由前缀。

---

## 4. 任务清单 (Commit 粒度)
*   **[E23-S1-T1]**：编写 DDL 迁移文件 `migrations/v2.1_add_maxim_tables.sql`。
*   **[E23-S1-T2]**：在测试库运行迁移，验证三张物理表及 `idx_user_category` 索引的建立。
*   **[E23-S1-T3]**：编写 Pydantic 校验模型 `app/models/checkin.py` 中的 `MaximQuoteCreate`，限制字数为 10-500 字。
*   **[E23-S1-T4]**：编写服务层 `app/services/checkin_service.py` 中 `create_quote()` 函数，完成插入并返回 ID。
*   **[E23-S1-T5]**：在 `app/api/checkin.py` 中注册路由 `POST /api/v1/checkin/maxim/quote`，挂载 `get_current_user_id` 验证。

---

## 5. 验收标准与测试用例映射 (AC → Test Case)

### AC1 手工录入成功落库与防空拦截
*   **Given** 用户已通过 Bearer Token 鉴权，且录入接口准备就绪；
*   **When** 提交格言字数小于 10 或大于 500 时；
*   **Then** 接口返回 `422 Unprocessable Entity` 校验错误；
*   **When** 提交 15 字合法金句时；
*   **Then** 接口返回 `200 OK` 并且包含新增自增 `quote_id`。
*   **映射测试**：`tests/test_checkin.py` 中 `test_e23_s1_create_quote_len_checks` 和 `test_e23_s1_create_quote_success`

### AC2 审计三件套与索引对账
*   **Given** 数据已录入到 `diary_quote_lib`；
*   **When** 查询数据库表记录时；
*   **Then** `created_at`、`updated_at` 等审计字段非空且为当前时区，且 `owner_user_id` 正确等于当前用户 ID。
*   **映射测试**：`tests/test_checkin.py` 中 `test_e23_s1_created_fields`
