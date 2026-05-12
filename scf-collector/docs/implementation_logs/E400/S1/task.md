# Tasks: E400-S1 P0 核心行情与因子同步

- [ ] **T1: 采集器能力扩展 (TushareCollector)**
    - [ ] 实现 `fetch_batch_daily_kline` (全 A 单日)
    - [ ] 实现 `fetch_adj_factor` (复权因子)
    - [ ] 实现 `fetch_index_daily` (指数行情)
    - [ ] 实现 `fetch_sw_industry_members` (拉链表逻辑)
- [ ] **T2: DAO 层存量对齐与扩展 (StockDAO)**
    - [ ] 实现 `save_adj_factor` (写入 `stock_adjust_factor`)
    - [ ] 实现 `save_industry_members` (写入 `dim_sw_industry_member`)
    - [ ] 优化 `save_kline_data` 支持大批量写入性能
- [ ] **T3: 函数逻辑集成 (daily_quotes & meta_sync)**
    - [ ] 在 `daily_quotes` 中集成 `sync_kline_daily` 与 `sync_adj_factor`
    - [ ] 在 `meta_sync` 中集成 `sync_sw_industry_member`
    - [ ] 确保 `meta_data_readiness` 信号准确触发
- [ ] **T4: 验证与存证**
    - [ ] 执行本地冒烟测试
    - [ ] 产出 `walkthrough.md` 与 `REPORT.md`
