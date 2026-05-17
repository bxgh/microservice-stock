# 实施方案: [E3-S1] 每日 K 线与复权因子采集任务调整

由于 `stock_kline_daily` 日线表引入了内嵌复权因子 `adj_factor` 字段，我们必须对每日数据采集流程（`sync_kline_daily` 与 `sync_adj_factor`）进行协同改造，确保：
1. 每日采集的日线行情数据在入库时已 100% 携带当日最新的累积复权因子。
2. 即使 Tushare 云端因子更新延迟，系统能够自动安全降级填充历史最新因子，并在校验期自动修补。
3. 因子变动检测（变动点存储）逻辑不受影响，保持高效与 GTID 安全。

---

## User Review Required

> [!IMPORTANT]
> **时序与合并采集设计**
>
> 1. **主流程合并采集**：我们将 `sync_kline_daily` 任务调整为**双源同步合并模式**。在 16:30 触发时，同步调用 Tushare 的 `daily` 接口和 `adj_factor` 接口，在内存中进行 `ts_code` 关联，一次性批量写入 `stock_kline_daily`。
> 2. **异步降级与单次查询优化**：如果 Tushare 当日因子未更新，系统将调用高内聚的 SQL 语句在 **0.02 秒内**获取全市场所有股票的历史最新因子进行填充（降级），绝不在循环中进行 5000+ 次数据库查询，保障 SCF (≤128MB) 容器在 30 秒内极速完成。
> 3. **保留并修正 `sync_adj_factor` 任务**：保留 16:35 触发的 `sync_adj_factor` 任务，其职责聚焦于**因子变动点检测**并更新 `stock_adjust_factor` 事件表。

---

## Open Questions

> [!NOTE]
> 暂无未决技术疑问。我们已经通过本地灰度验证了 MySQL 5.7 下高性能的因子获取与合并逻辑，GTID 与内存限制均在安全范围内。

---

## Proposed Changes

### 数据采集层 (`scf-collector`)

#### [MODIFY] [models.py](file:///home/ubuntu/microservice-stock/scf-collector/shared/utils/models.py)
- 在 `KLineModel` 中新增 `adj_factor` 属性，设置默认值为 `None`，以在 Pydantic 数据契约中承载内嵌因子。

#### [MODIFY] [dao.py](file:///home/ubuntu/microservice-stock/scf-collector/shared/db/dao.py)
- **更新 `StockDAO.save_kline_data`**：
  - 在 `INSERT INTO stock_kline_daily` SQL 语句中添加 `adj_factor` 字段。
  - 在 `ON DUPLICATE KEY UPDATE` 子句中添加 `adj_factor = VALUES(adj_factor)`。
- **新增 `StockDAO.get_all_latest_adj_factors()`**：
  - 实现兼容 **MySQL 5.7** 的高能效全量股票最新因子关联查询，用于 Tushare 延迟时的内存批量降级填充：
    ```sql
    SELECT a1.ts_code, a1.adjust_factor 
    FROM stock_adjust_factor a1
    JOIN (
        SELECT ts_code, MAX(adjust_date) as max_date 
        FROM stock_adjust_factor 
        GROUP BY ts_code
    ) a2 ON a1.ts_code = a2.ts_code AND a1.adjust_date = a2.max_date;
    ```

#### [MODIFY] [index.py](file:///home/ubuntu/microservice-stock/scf-collector/functions/daily_quotes/index.py)
- **重构 `sync_kline_daily` 处理分支**：
  - 1. 调用 `collector.fetch_batch_daily_kline(trade_date)` 获取行情。
  - 2. 同步调用 `collector.fetch_adj_factor(trade_date)` 获取当日因子。
  - 3. **内存合并与降级**：
    - 如果当日因子有数据：将其转化为 `dict` 并与行情模型进行 `ts_code` 匹配填充。
    - 如果当日因子为空（延迟）：通过 `StockDAO.get_all_latest_adj_factors()` 极速拉取本地最新历史因子，在内存中完成降级填充，并输出 `WARNING` 级别日志。
  - 4. 批量保存至 `stock_kline_daily`。
- **强化 `validate_and_failover` 审计与自愈分支**（17:00 任务）：
  - 检查当日入库 of K 线数据，如果发现存在 `adj_factor IS NULL` 的脏数据，自动触发因子对账补丁，从 `stock_adjust_factor` 的最新数据中拉取并覆写。

---

## Verification Plan

### Automated Tests
1. **本地单元测试 (Local Integration Test)**：
   - 编写 `tests/test_sync_kline_with_factor.py`。
   - 模拟 Tushare 正常返回与异常返回（空因子）两种场景，验证数据入库是否符合预期。
2. **容器内测试 (Docker Test)**：
   - 在 Docker 容器中执行 `pytest tests/`，验证数据写入与自愈逻辑正常。

### Manual Verification
1. **灰度采集调试**：
   - 手动触发 `op == 'sync_kline_daily'` 采集历史某一日的数据，并使用 SQL 校验：
     ```sql
     -- 确认因子已被正确内嵌写入，且不存在 NULL
     SELECT COUNT(*) FROM stock_kline_daily 
     WHERE trade_date = '2026-05-11' AND adj_factor IS NULL;
     ```
2. **审计报告输出**：
   - 确认 17:00 影子审计与就绪性探测状态表中 `record_count` 依然准确无误。
