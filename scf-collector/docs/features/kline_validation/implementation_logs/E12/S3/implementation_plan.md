# E12-S3 实施计划：任务化自动修复引擎

本 Story 旨在构建一套能够自动消费 `meta_task_queue` 中 `HOLE` 类型任务的修复管线。

## 用户审核

> [!IMPORTANT]
> **API 额度预警**：修复逻辑会优先调用 Tushare。如果空洞分布在大量不同交易日，可能会消耗较多积分。我们将通过“按天聚合修复”来最大化单次调用的价值。

## 待办任务

### [E6] 修复引擎开发

#### [NEW] [auto_repair_worker.py](file:///home/ubuntu/microservice-stock/scf-collector/scripts/auto_repair_worker.py)
核心修复逻辑：
- 扫描 `meta_task_queue` 中 `status='PENDING'` 的任务。
- 按 `trade_date` 进行聚合分包。
- 调用 `TushareCollector` 获取缺失数据。
- 状态闭环：成功后更新任务状态，失败记录 `retry_count`。

#### [MODIFY] [TushareCollector](file:///home/ubuntu/microservice-stock/scf-collector/shared/collectors/tushare_cl.py)
增强其鲁棒性，支持单日强制重采模式。

## 验证计划

### 自动化验证
- 模拟一个缺失数据场景：手动删除某日某股记录，写入任务队列，运行 `auto_repair_worker.py`，核实数据是否恢复。

### 幂等性测试
- 重复运行修复任务，确保数据库不产生重复数据。
