- [ ] **E1 预备环境 (Env Readiness)**
    - [x] 确认 MySQL 5.7 连通性与权限
    - [x] 确认 `stock_kline_daily` 字段结构 (已包含 `adj_factor`)
    - [x] 确认宿主机磁盘空间 (7.6GB Avail vs 1.37GB Table)

- [x] **E2 历史数据回填 (Backfill Execution)**
    - [x] **E2-S1-T1**: 物理备份 `stock_kline_daily_bak_20260515` (已在 DB 内完成备份)
    - [x] **E2-S1-T2**: 确认 `stock_adjust_factor` 联合索引
    - [x] **E2-S1-T3**: 编写并部署 `backfill_adj_factor.py` (已部署至 `stock-manager` 容器)
    - [/] **E2-S1-T4**: 启动容器化批量回填并监控日志 (进行中，ETA ~4h)

- [ ] **E3 验证与审计 (Verification & Audit)**
    - [ ] **E3-S1-T1**: 执行空值审计 (Target: 0)
    - [ ] **E3-S1-T2**: 10只个股前复权对账验证
    - [ ] **E3-S1-T3**: 产出回填完成报告 (REPORT.html)
