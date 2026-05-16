# Task List - E12-S1-T1

- [x] **T1-0: 基础设施准备 (Migration)**
    - 执行 DDL 创建 `meta_task_queue` 表。
    - 在 `meta_config` 中初始化 `kline_audit_cursor`。
- [x] **T1-1: 脚本架构与三源抽象层**
    - 实现 `TushareClient` 与 `AkShareClient` 的统一调用接口。
    - 引入 `Arbitrator` 类处理 `(Local, Tushare, AkShare)` 的三方对账逻辑。
- [x] **T1-2: 每日全市场对账引擎**
    - 实现以“天”为单位的 `daily_chunk_iterator`。
    - 编写数值对账逻辑（OHLC、成交量、成交额）。
- [/] **T1-3: 因子表专项巡检 (stock_adjust_factor)**
    - 针对 `stock_adjust_factor` 的全量完整性检查。
    - 验证 K 线表中的内嵌因子与因子表记录的对应关系。
- [x] **T1-4: 断点续传与元数据状态管理**
    - 在 `meta_config` 中记录巡检进度。
    - 支持 `--start_date` 和 `--end_date` 参数，实现任务可重入。
- [ ] **T1-5: 审计报告生成 (REPORT.html)**
    - 统计总对账行数、错误分布、自动标记为修复状态的比例。
