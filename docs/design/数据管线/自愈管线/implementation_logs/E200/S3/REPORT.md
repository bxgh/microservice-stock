# [E200-S3] 技术报告：级联失效与同步阻塞 (Consistency)

## 1. 背景与目标
在自愈管线中，修复 MySQL 侧的数据后，若下游（ClickHouse/ADS）未能及时感知并同步更新，会导致分析系统读取到“脏数据”。
本 Story 实现了 **Stage F (同步阻塞)** 与 **Stage G (级联失效)**，确保修复后的数据具有强一致性。

## 2. 核心方案实现

### 2.1 同步阻塞 (Stage F)
- **机制**: 在 `HealerService` 执行 UPDATE 操作后，记录当前的基准 `last_commit_lsn`。
- **轮询**: 通过 `wait_for_sync_ack` 轮询 `meta_sync_status` 表，直到 `last_commit_lsn` 增加，表明同步网关已完成数据迁移。
- **超时降级**: 若 60s 内未收到 ACK，系统会自动将修复记录标记为 `ORPHAN` (孤儿状态)，并触发告警，以提示下游读取可能存在滞后。

### 2.2 级联失效 (Stage G)
- **配置**: 在 `lineage.yaml` 中新增了 `ads_kline_adj`, `ads_indicator_ma`, `ads_strategy_signal` 等关键下游依赖。
- **信号**: 增强 `backfill_service.py` 中的 `invalidate_downstream` 方法，在数据修复后自动清理上述表中的对应记录，并向 `recalc_signal` 插入重算指令。

## 3. 交付清单
- **DDL**: `20260511_create_meta_sync_status.sql`, `20260511_add_sync_lsn_to_repair_log.sql`
- **代码**: 
    - `healer_service.py`: 增加 `wait_for_sync_ack` 及同步状态追踪。
    - `backfill_service.py`: 优化级联清理逻辑。
- **配置**: `lineage.yaml` 下游血缘补全。

## 4. 风险评估
- **网关依赖**: 当前实现依赖外部同步网关更新 `meta_sync_status`。若网关失效，修复任务将频繁触发 `ORPHAN` 告警。
- **并发压力**: 轮询间隔设为 2s，在高并发修复场景下对数据库元数据表有一定查询压力。
