# 指令队列格式规范 (task_commands)

本文档定义了前端或外部系统向 **AlwaysUp** 任务指令队列下达命令时的标准格式。

## 1. 数据库表结构 (Schema)
目标数据库：`alwaysup`  
目标表名：`task_commands`

| 字段名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| **`task_id`** | `VARCHAR(64)` | 是 | 后端任务标识符 (见下表) |
| **`params`** | `JSON` | 是 | 参数字典，必须为合法的 JSON 字符串 |
| **`status`** | `ENUM` | 是 | 固定写入 `'PENDING'`，等待后端抓取 |
| **`result`** | `TEXT` | 否 | 执行结果或错误日志 (由后端回写) |

## 2. 标准指令内容 (Commands)

| 业务场景 | `task_id` | `params` 示例 | 执行效果 |
| :--- | :--- | :--- | :--- |
| **同步股票名单** | `sync_stock_list` | `{}` | 强制同步全量名单镜像到 Redis |
| **补采分笔数据** | `repair_tick` | `{"date": "20260115"}` | 重新抓取指定日期的 Tick 数据 |
| **补采日线 K 线** | `repair_kline` | `{"date": "20260115"}` | 重新抓取指定日期的日 K 线数据 |

## 3. 指令生命周期状态
前端可根据 `status` 字段实现 UI 逻辑：
- **`PENDING`**: (前端写入) 指令已入队，等待处理。
- **`RUNNING`**: (后端更新) 任务正在内网容器中执行。
- **`DONE`**: (后端更新) 指令执行成功。
- **`FAILED`**: (后端更新) 执行失败，详情见 `result` 字段。

## 4. SQL 插入示例 (参考)
```sql
-- 示例：触发补采 2026-01-15 的分笔数据
INSERT INTO alwaysup.task_commands (task_id, params, status) 
VALUES (
    'repair_tick', 
    '{"date": "20260115"}', 
    'PENDING'
);
```
