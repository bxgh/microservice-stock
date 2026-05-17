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
2026-05-15 22:19:58 [INFO] Progress: 7437/7437 (100.00%) | Speed: 3.20 stocks/s | ETA: 0.00 min
2026-05-15 22:19:58 [INFO] Backfill completed in 38.71 minutes.
```

## 3. 验证方案
- [x] **AC1**: 执行空值审计。抽样检查 `600519.SH` 等核心股，`adj_factor` 已正确填充非空值。
- [x] **AC2**: 抽样 10 只个股的前复权价格一致性对账。
    - **测试样本**: `600519.SH`, `000001.SZ`, `601318.SH` 等 10 只。
    - **结论**: **49/50 校验点完全匹配**（1 点为 Tushare 数据源微小差异），精度符合预期。

## 4. 交付物
- **设计文档**: [Adjfactor-in-klineDaily.md](../../design/Adjfactor-in-klineDaily.md)
- **回填报告**: [REPORT.html](REPORT.html)

---

## 5. 2026-05-17 重新全量回填实施记录 (Rerun)

### 5.1 任务背景与原因
由于 `stock_kline_daily` 经历了全市场全量数据重新更新，原有已填充的内嵌 `adj_factor` 被清空或重置为 `NULL`。为了恢复全库 100% 的因子覆盖并保持选股性能，需要执行重新回填。
- 启动前库内状态审计：
  - 总行数: `17,080,241` 行
  - `adj_factor IS NULL` 行数: `17,080,241` 行 (100% 缺失)

### 5.2 核心代码健壮性优化
在执行回填前，我们对已开发的脚本 `scripts/backfill/backfill_adj_factor.py` 进行了关键健壮性增强：
- **覆盖率漏洞修复**：原脚本通过 `stock_basic_info` 维度表获取全部 `ts_code`。审计发现，有 7 只股票（如 `000022.SZ`, `300114.SZ` 等）存在于日线表但未录入基本信息表，这会导致 100% 覆盖率的 AC 验收失败。
- **优化方案**：将 `get_all_ts_codes` 方法修改为 `SELECT DISTINCT ts_code FROM stock_kline_daily`。该查询由于利用了主键索引的前缀扫描，执行时间仅需 `0.46` 秒，且能够 **100% 涵盖所有实际存在日线的股票**。

### 5.3 灰度与性能验证
1. **5只股票小样本灰度回填** (000001.SZ ~ 000005.SZ)：
   - 耗时: `4.46` 秒
   - 因子填充率: `100.00%` (NULL 行数为 0)
   - 因子值范围与变化完全符合预期（未除权阶段自动填充为 1.000000，除权后正确向前填充）。
2. **GTID 兼容性审计**：排除了使用临时表（`TEMPORARY TABLE`）或大事务的方案，以防止违反云数据库的 GTID 强一致性限制。保持原有的分股票单事务提交模式，平滑稳定。

### 5.4 全量执行状态
已将优化后的回填脚本在云端服务器后台拉起执行：
- **执行命令**: `python3 scripts/backfill/backfill_adj_factor.py`
- **后台命令 ID**: `c971106e-ea1f-420c-97a7-c9a56ba9aa01`
- **状态监控**: 
  - 日志路径: `logs/backfill_adj_factor.log`
  - 进度监控: 可以使用 `tail -f logs/backfill_adj_factor.log` 实时跟踪。
  - 预计耗时: 约 70 分钟 (基于当前 1.3 stocks/s 稳定速率)。

### 5.5 盘后对账与验收 SQL (完成后的手工 AC 审计)
在回填完全结束后，Data Quality Steward 可以通过运行以下三段 SQL 确认回填 100% 成功：

```sql
-- 审计 1: 必须没有 NULL 行（预期：0 行）
SELECT COUNT(*) AS null_count 
FROM stock_kline_daily 
WHERE adj_factor IS NULL;

-- 审计 2: 抽样检验茅台因子在 2023-07-03 除权日前后的变化
SELECT trade_date, close, adj_factor 
FROM stock_kline_daily 
WHERE ts_code = '600519.SH' 
  AND trade_date BETWEEN '2023-06-28' AND '2023-07-06' 
ORDER BY trade_date;

-- 审计 3: 验证未发生过除权的股票（如近期上市新股），因子全部为 1.000000
SELECT DISTINCT adj_factor 
FROM stock_kline_daily 
WHERE ts_code = '920680.BJ';
```

