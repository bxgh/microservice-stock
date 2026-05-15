# [E2] 历史数据回填 - 复权因子内嵌

## 1. 目标描述
将 `stock_adjust_factor` 中的变动点因子数据“展开”回填至 `stock_kline_daily` 表中的 `adj_factor` 字段。由于 `stock_kline_daily` 数据量达到 **1922万行**，且环境为 MySQL 5.7（不支持高级窗口函数），直接使用单条 SQL `UPDATE` 会导致长时间锁表和高 CPU 负载。本计划采用 **Python 批量处理 + 股票维度事务** 的方式进行平滑回填。

## 2. 待评审事项 (User Review Required)
> [!IMPORTANT]
> **物理环境与资源约束**：
> - **执行环境**：回填任务必须在 **腾讯云服务器的 Docker 容器** 内运行（如 `stock-manager` 或专用的 `batch-job` 容器），严禁在 SCF 云函数环境执行（避免超时与内存限制）。
> - **磁盘空间预警**：`stock_kline_daily` 当前库内占用约 **1.37 GB**。宿主机可用空间为 **7.6 GB**，足以支撑本次备份与回填操作。
> - **性能与安全策略**：
>   - 采用 **“逐股票处理”** 模式：每次开启事务处理一只股票的所有历史行，完成后提交。这样可以将单次事务限制在 5000 行左右（平均上市天数），避免大事务锁表。
>   - **跳过已有值**：脚本具备幂等性，仅回填 `adj_factor IS NULL` 的行，支持断点续传。

## 3. 核心设计 (Architecture)

### 3.1 回填算法：Forward-Fill
1. 获取待处理的 `ts_code` 列表。
2. 对于每个 `ts_code`：
    - 从 `stock_adjust_factor` 获取该股所有因子变动点（按日期升序）。
    - 获取该股在 `stock_kline_daily` 中所有 `adj_factor` 为空的记录（按日期升序）。
    - 遍历 K 线记录，将 `adj_factor` 设置为 **<= 当前交易日的最新变动点因子**。
    - 若交易日早于第一个变动点，则填充 `1.0`。
3. 执行 `UPDATE` 语句。

### 3.2 进度监控与日志 (Monitoring & Logging)
- **日志记录**：使用标准的 Python `logging` 模块，记录详细的执行日志。
- **进度输出**：
    - **每处理 50 只股票** 输出一次当前进度（已处理数/总数、百分比）。
    - **耗时预估**：根据当前处理速度，动态计算并输出剩余时间 (ETA)。
- **日志文件**：日志将同步写入 `logs/backfill_adj_factor.log`，方便用户使用 `tail -f` 实时跟踪。
- **状态持久化**：每批次执行成功后记录一次检查点，支持异常中断后的快速续跑。

## 4. 拟定变更 (Proposed Changes)

### [scf-collector]

#### [NEW] [backfill_adj_factor.py](file:///home/ubuntu/microservice-stock/scripts/backfill/backfill_adj_factor.py)
实现高效回填逻辑的 Python 脚本。
- 使用 `pymysql` 直接连接数据库以获得最高性能。
- 包含进度条和耗时预估。
- 错误重试机制。

#### [MODIFY] [TABLES_INDEX.md](file:///home/ubuntu/microservice-stock/docs/TABLES_INDEX.md)
更新 `stock_kline_daily` 的元数据定义，明确 `adj_factor` 字段已进入生产回填阶段。

## 5. 验证计划 (Verification Plan)

### 5.1 自动化测试 (QC)
- **空值检查**：执行 `SELECT COUNT(*) FROM stock_kline_daily WHERE adj_factor IS NULL`，预期为 0。
- **前复权一致性校验**：
    - 随机抽取 **至少 10 只个股**（覆盖高频除权股如：`600519.SH`, `000001.SZ`, `601318.SH` 等）。
    - 调取 Tushare 官方前复权行情作为基准。
    - 使用公式 `adj_close = close * adj_factor / latest_adj_factor` 验证本地计算结果。
    - 允许误差范围：$10^{-4}$ (由于浮点数精度)。
- **极端情况验证**：验证新上市（从未除权）的股票，因子应全为 `1.0`。

### 5.2 手动验证
- 随机抽查茅台 (`600519.SH`) 在除权日（如 2023-07-03）前后的因子跳变情况。

## 6. 任务拆解 (Task Breakdown)
- [x] **E2-S1-T1**: 物理备份（导出 `stock_kline_daily` 的 `ts_code, trade_date, adj_factor` 备份）。
- [x] **E2-S1-T2**: 确认 `stock_adjust_factor` 上存在 `(ts_code, adjust_date)` 联合索引（已确认）。
- [x] **E2-S1-T3**: 编写并执行 `backfill_adj_factor.py` 脚本。
- [/] **E2-S1-T4**: 执行审计 SQL 并产出回填报告。
