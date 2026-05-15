# 实施日志: [E2-S1] 因子 Forward-Fill 回填

## 1. 任务背景
针对 `stock_kline_daily` 存量数据（1922万行）进行 `adj_factor` 字段的物理回填，旨在消除全市场选股时的 JOIN 开销。

## 2. 实施细节

### 2.1 物理备份 (E2-S1-T1)
由于生产环境开启了 GTID 且数据量较大，采用在库内创建快照表的方式进行备份。
- **备份表名**: `stock_kline_daily_bak_20260515`
- **数据量**: 19,226,760 行
- **备份耗时**: 约 4 分钟

```sql
-- 验证备份表
SELECT COUNT(*) FROM stock_kline_daily_bak_20260515;
-- 结果: 19226760
```

### 2.2 脚本部署与执行 (E2-S1-T3)
脚本 `scripts/backfill/backfill_adj_factor.py` 已部署至 `stock-manager` 容器。
- **执行环境**: Docker 容器 (Tencent Cloud)
- **核心逻辑**: 采用股票维度 (ts_code) 的分批更新，每 50 只股票输出一次进度，每只股票事务独立提交。

### 2.3 进度监控 (E2-S1-T4)
实时监控日志输出：
```text
2026-05-15 21:42:49 [INFO] Progress: 50/7437 (0.67%) | Speed: 0.53 stocks/s | ETA: 231.25 min
...
2026-05-15 22:02:35 [INFO] Progress: 3300/7437 (44.37%) | Speed: 2.58 stocks/s | ETA: 26.74 min
```

## 3. 验证方案 (Pending)
- [ ] **AC1**: 执行空值审计，预期 `adj_factor IS NULL` 数量为 0。
- [ ] **AC2**: 抽样 10 只个股（含茅台）的前复权价格一致性对账。

## 4. 交付物
- **设计文档**: [Adjfactor-in-klineDaily.md](../../design/Adjfactor-in-klineDaily.md)
- **技术报告**: [REPORT.html](REPORT.html) (自动生成)
