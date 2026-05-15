# Implementation Plan - E8-S1: 变动检测写入 (Change-based Storage for Adj Factors)

本项目旨在优化 `stock_adjust_factor` 的存储逻辑，从“每日全量”切换为“变动事件”存储。本计划聚焦于 `scf-collector` 的 DAO 层实现。

## 需求解析
- **核心逻辑**：在写入复权因子前，先查询库中该股票最新的因子值。仅当新因子与旧因子存在显著差异（误差 > 1e-8）时，才插入新记录。
- **存储对齐**：插入时，`back_adjust_factor` 和 `adjust_factor` 填入相同值，`fore_adjust_factor` 显式设为 `NULL` 以标记废弃。
- **幂等性**：同一交易日的重复调用应通过逻辑判断（因子未变）自动跳过，不产生冗余记录。

## 依赖认证
- **数据表**：`stock_adjust_factor` (MySQL 5.7)。
- **字段要求**：需包含 `ts_code`, `adjust_date`, `adjust_factor`, `fore_adjust_factor`, `back_adjust_factor`。
- **环境**：腾讯云 SCF (Python 3.10)。

## 架构溯源与风险认证
- **激活角色**: [Requirement Architect], [Backend Engineer], [DB Auditor], [Data Quality Steward], [Workflow Guard]
- **风险**:
    - **性能风险**：每条插入前增加一次查询，在批量（5000+）时可能增加耗时。需确保 `(ts_code, adjust_date DESC)` 索引命中。
    - **数据丢失**：若查询逻辑错误导致漏记变动点，将影响下游复权。
- **缓解措施**：
    - 使用 `ORDER BY adjust_date DESC LIMIT 1` 配合索引。
    - 浮点数比对使用 `1e-8` 阈值。

## 方案设计

### 1. DAO 层逻辑重构
修改 `scf-collector/shared/db/dao.py` 中的 `StockDAO.save_adj_factor`。

- **逻辑流程**:
    1. 接收 `data` 列表（由 TushareCollector 传入）。
    2. 遍历 `data`。
    3. 对每个 `ts_code`，查询 `stock_adjust_factor` 中最新的 `adjust_factor`。
    4. 对比新旧值：`abs(new - old) > 1e-8`。
    5. 若变化或无记录：执行 `INSERT`。
    6. 若未变化：跳过。

### 2. SQL 语句优化
- **查询 SQL**:
    ```sql
    SELECT adjust_factor FROM stock_adjust_factor 
    WHERE ts_code = %s 
    ORDER BY adjust_date DESC 
    LIMIT 1
    ```
- **插入 SQL**:
    ```sql
    INSERT INTO stock_adjust_factor 
        (ts_code, adjust_date, fore_adjust_factor, back_adjust_factor, adjust_factor)
    VALUES (%(ts_code)s, %(adjust_date)s, NULL, %(adj_factor)s, %(adj_factor)s)
    ```

## 任务列表 (Tasks)
- [ ] **E8-S1-T1**: 修改 `dao.py` `save_adj_factor` 实现查询比对逻辑。
- [ ] **E8-S1-T2**: 调整插入字段，设置 `fore=NULL` 及 `back=adjust`。
- [ ] **E8-S1-T3**: 编写本地测试脚本验证幂等性和变动写入。

## 验收标准 (AC)
- **AC1: 幂等性验证**
    - Given: `600519.SH` 最新因子为 `1.234`。
    - When: 再次写入 `1.234`。
    - Then: 数据库行数不变。
- **AC2: 变动写入验证**
    - Given: `600519.SH` 最新因子为 `1.234`。
    - When: 写入新因子 `1.356`。
    - Then: 产生一条新记录，且 `back_adjust_factor` 对齐。
