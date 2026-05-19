# Epic E23-S1: 格言库建表与手工录入接口 · 任务清单

- [x] `[x]` T1: 编写 DDL 迁移文件 `migrations/v2.1_add_maxim_tables.sql`
- [x] `[x]` T2: 在测试库运行迁移，验证三张物理表及 `idx_user_category` 索引的建立
- [x] `[x]` T3: 编写 Pydantic 校验模型 `app/models/checkin.py` 中的 `MaximQuoteCreate`，限制字数为 10-500 字
- [x] `[x]` T4: 编写服务层 `app/services/checkin_service.py` 中 `create_quote()` 函数，完成插入并返回 ID
- [x] `[x]` T5: 在 `app/api/checkin.py` 中注册路由 `POST /api/v1/checkin/maxim/quote`，挂载 `get_current_user_id` 验证
