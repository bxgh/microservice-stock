# Task List - E200-S1: 差异化跨源扫描器

- [x] `[E200-S1-T1]` **Mootdx 集成**: 在 `stock-manager-api` 的 `http_client` 中配置 `mootdx-api` 路由。
- [x] `[E200-S1-T2]` **模型适配**: 封装 `Mootdx` 返回的 K 线数据模型，使其与 ODS 结构对齐。
- [x] **[E200-S1-T3]** **仲裁逻辑开发**:
    - [x] 实现 OHLCV 的“取二一致”判定算法。
    - [x] 实现针对财务勾稽的单源逻辑审计。
- [x] `[E200-S1-T4]` **集成测试**: 编写并运行 `test_e200_s1_arbitration.py`。
- [x] `[E200-S1-T5]` **审计存证**: 确认异常结果能够正确写入 `dq_findings` 表并包含 `diff_data` 详情。
