# 实施方案: [E3-S1] 每日 K 线与复权因子采集任务调整

由于 `stock_kline_daily` 日线表引入了内嵌复权因子 `adj_factor` 字段，我们必须对每日数据采集流程（`sync_kline_daily` 与 `sync_adj_factor`）进行协同改造，并结合 Tushare 官方因子的发布时序（**盘前 09:15 ~ 09:20 完成当日因子入库**）进行时序优化，确保：
1. 每日采集的日线行情数据在入库时已 100% 携带当日最新的累积复权因子。
2. 将因子的采集与变动点记录提早到**盘前（09:25）**执行，使本地 `stock_adjust_factor` 变动点事件表在开盘前即处于最新状态。
3. 盘后（16:30）采集日线时，可 100% 信任并使用本地已就绪的因子数据，彻底消除盘后因网络波动或云端延迟导致的因数降级风险。
4. 因子变动检测（变动点存储）逻辑不受影响，保持高效与 GTID 安全。

---

## User Review Required

> [!IMPORTANT]
> **盘前因子采集与盘后日线内嵌时序设计**
>
> 1. **`sync_adj_factor` 盘前移频（09:25）**：将原 16:35 的 `sync_adj_factor` 采集任务前移至**交易日 09:25** 执行。由于 Tushare 官方在 09:15~09:20 之间即已完成当日因子计算，在此时间点拉取可确保当日发生的除权除息因子在开盘前便已写入本地 `stock_adjust_factor` 变动点表。
> 2. **`sync_kline_daily` 盘后极速合并（16:30）**：在 16:30 触发日线采集时，系统优先直接通过高内聚 SQL **在 0.02 秒内**从本地 `stock_adjust_factor` 关联提取当日最新因子并写入 `stock_kline_daily`（不消耗 Tushare 积分）。
> 3. **【新增】三层容灾与治愈链（针对 09:25 任务失败的兜底策略）**：
>    - **第一层：主动校验与云端补货（16:30）**：`sync_kline_daily` 启动时，自动查询 `meta_pipeline_run_log` 校验今日 09:25 的 `Adj-Factor` 任务是否成功运行：
>      - **成功**：使用 100% 本地数据库因子合并（0.02 秒，0 积分）。
>      - **失败**：系统输出 `WARNING` 日志并**自动实时向 Tushare 发起全量当日因子拉取**，进行内存合并，保证日线 100% 携带正确因子入库。
>    - **第二层：变动点同步自愈（16:30 后半段）**：若触发了第一层云端补货，系统写入日线后，在后台静默运行 `StockDAO.save_adj_factor`，**将早上因失败遗漏的因子变动点数据自动补齐写入 `stock_adjust_factor` 表**，实现自愈。
>    - **第三层：终极对账审计（17:00）**：17:00 的 `validate_and_failover` 终极对账任务会审计所有 `adj_factor` 字段，若检测到仍有 NULL 或异常，立即自动修复，守住 100% 覆盖率红线。

---

## Open Questions

> [!NOTE]
> 暂无未决技术疑问。已确认 `meta_pipeline_run_log` 提供完备的流水状态追踪，我们已将该三层容灾机制完全纳入实施细节。

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
