# E12-S1 实施计划：全量完整性空洞审计

本 Story 旨在对重采后的 2000 万+ 条 K 线数据进行彻底的完整性检查。我们将通过“理论应有量”与“数据库实有量”的对账，发现并记录所有缺失的 K 线数据。

## 用户审核

> [!IMPORTANT]
> **资源开销预警**：全量对账涉及对 1990 年至今所有个股上市状态的计算。为了不影响生产库性能，审计脚本将采用 **Chunking (分年/分月)** 模式执行，并在腾讯云 Docker 环境中运行。

## 待办任务

### [L2] 完整性审计器开发

#### [NEW] [check_kline_holes.py](file:///home/ubuntu/microservice-stock/scf-collector/scripts/check_kline_holes.py)
实现核心审计逻辑：
- 加载交易日历与个股基础信息。
- 计算每日理论股票池。
- 执行快速 `GROUP BY` 筛查。
- 执行深度 `set_diff` 审计，找出缺失 `ts_code`。

#### [NEW] [REPORT.html](file:///home/ubuntu/microservice-stock/scf-collector/docs/features/kline_validation/implementation_logs/E12/S1/REPORT.html)
动态生成的审计报告，展示空洞分布热力图。

## 验证计划

### 自动化验证
- 运行 `pytest tests/test_integrity_checker.py`：验证理论计数的正确性（选取已知停牌或退市个股作为测试用例）。

### 手动核验
- 随机抽取报告中标记为“空洞”的一个 `ts_code` + `trade_date`，在 Tushare 官方网页版或 AkShare 接口中核实其真实性（排除停牌干扰）。
