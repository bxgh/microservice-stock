# [E200-S3] 级联失效与同步阻塞 (Consistency)

## 核心逻辑描述
本 Story 旨在解决自愈修复后的“一致性滞后”问题。修复 MySQL ODS 数据后，必须确保：
1. **同步阻塞 (Stage F)**: 确认修复后的数据已成功同步至 ClickHouse (CK)，防止下游读取到旧的损坏数据。
2. **级联失效 (Stage G)**: 自动清理并标记下游受影响的 ADS 视图（如复权 K 线、指标、信号），强制重算以保证全链路数据正确性。

## 角色激活
- [Data Quality Steward]: 负责一致性契约与同步位点设计。
- [Backend Developer]: 负责阻塞等待逻辑与级联信号实现。

## User Review Required
> [!IMPORTANT]
> 引入 `meta_sync_status` 表用于记录腾讯云同步网关的确认位点 (`commit_lsn`)。
> 若同步网关尚未部署，`HealerService` 将采用模拟 ACK 机制或超时降级。

## Proposed Changes

### 1. 数据库变更 (DDL)
#### [NEW] [20260511_create_meta_sync_status.sql](file:///home/ubuntu/microservice-stock/migrations/20260511_create_meta_sync_status.sql)
- 建立 `meta_sync_status` 表，记录各表的同步位点。
- 字段：`table_name`, `last_commit_lsn`, `last_sync_at`, `status`.

#### [NEW] [20260511_add_sync_lsn_to_repair_log.sql](file:///home/ubuntu/microservice-stock/migrations/20260511_add_sync_lsn_to_repair_log.sql)
- 为 `meta_repair_log` 增加 `sync_lsn` 和 `sync_status` 字段。

---

### 2. 配置与血缘 (Core)
#### [MODIFY] [lineage.yaml](file:///home/ubuntu/microservice-stock/stock-manager-api/app/core/lineage.yaml)
- 完善 `stock_kline_daily` 的下游依赖：
  - `ads_kline_adj` (复权线)
  - `ads_indicator_ma` (均线)
  - `ads_strategy_signal` (信号)

---

### 3. 核心服务 (Services)
#### [MODIFY] [backfill_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/backfill_service.py)
- 增强 `invalidate_downstream()`:
  - 完善清理逻辑，支持对 ADS 视图的 `DELETE` 或 `UPDATE status='STALE'`。
  - 确保发送 `recalc_signal` 信号。

#### [MODIFY] [healer_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/healer_service.py)
- 实现 `wait_for_sync_ack(table_name, target_lsn, timeout=60)`:
  - 轮询 `meta_sync_status` 表。
  - 超时则记录 `sync_status = 'ORPHAN'` 并告警。
- 更新 `repair_finding()`:
  - 在写入 ODS 后，执行 `wait_for_sync_ack`。
  - 只有在同步确认或超时处理后，才触发 `invalidate_downstream`。

---

## 验证计划

### 自动化测试
1. **同步阻塞验证**:
   - 模拟修复操作。
   - 手动向 `meta_sync_status` 写入对应的 `commit_lsn`。
   - 验证 `healer_service` 能在收到 ACK 后继续执行。
   - 验证超时 60s 后状态标记为 `ORPHAN`。
2. **级联失效验证**:
   - 修复 `stock_kline_daily` 中的某条记录。
   - 检查 `ads_kline_adj` 是否被清理。
   - 检查 `recalc_signal` 是否新增了重算任务。

### 手动验证
- 观察 `logs/stock-manager.healer.log` 中的 "Sync ACK received" 或 "Sync timeout - downgraded to ORPHAN" 记录。
