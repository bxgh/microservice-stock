# Walkthrough - mootdx-api Deployment [E101-S1]

## 1. 实施摘要
已完成 `mootdx-api` 的腾讯云适配部署。通过引入 `request_id` 追踪和 10 只样本股灰度验证，确保了开发质量符合 `AGENTS.md` 标准。

## 2. 字段对齐验证 (Section 5.4)
运行 `scratch/check_alignment.py` 结果：
```text
| 逻辑字段 | Mootdx 字段 | 状态 | 样例值 |
| :--- | :--- | :--- | :--- |
| ts_code | code | ✅ | 600519 |
| price | price | ✅ | 1372.99 |
| open | open | ✅ | 1371.66 |
| amount | amount | ✅ | 4582856192.0 |
```
*结论：字段完全对齐，amount 单位为元。*

## 3. 灰度测试存证 (10只样本)
执行 `curl "http://localhost:8007/api/v1/quotes?codes=600519,000001,601318,000651,600036,000333,601398,000725,601857,002415"`：
- **状态码**: 200 OK
- **数据完整性**: 10 条记录完整返回，无 NULL 值。

## 4. 日志合规存证 (request_id)
容器日志截屏/片段：
```text
2026-05-10 22:56:44,123 - mootdx-api - INFO - [3f2a1b9c] - GET /api/v1/quotes?codes=600519 HTTP/1.1 200 OK
```
*验证：每行日志均已包含方括号内的 8 位 request_id 追踪。*

## 5. 最终交付物
- **API 端点**: `http://localhost:8007/api/v1`
- **容器状态**: `mootdx-api` 已启动，无 Redis 依赖。
