# Implementation Plan - E400-S1: P0 核心行情与因子同步 (Batch Implementation)

针对 `E400_SCF_Collector_Implementation.md` 中的 S1 阶段，实现日 K 线（不复权）、复权因子、申万行业成员及行业指数的生产级批量同步逻辑。

## Readiness Check
- [x] **需求解析**: 实现 5000+ 股票的批量 K 线及复权因子同步，补齐申万行业维表，消除 Schema 漂移。
- [x] **依赖认证**: Tushare Pro 接口权限确认；MySQL 存量表名（`stock_kline_daily`, `stock_adjust_factor`）确认。
- [x] **角色激活**: [Python Backend Engineer], [Data Quality Steward].

## Proposed Changes

### 1. 采集器层 (shared/collectors/)

#### [MODIFY] [tushare_cl.py](file:///home/ubuntu/microservice-stock/scf-collector/shared/collectors/tushare_cl.py)
- 增加 `fetch_batch_daily_kline(trade_date)`: 调用 `pro.daily` 获取全 A 单日 K 线。
- 增加 `fetch_adj_factor(trade_date)`: 调用 `pro.adj_factor` 获取全 A 单日复权因子。
- 增加 `fetch_sw_industry_members()`: 调用 `pro.index_member_all()` 获取申万行业成员拉链数据。
- 增加 `fetch_index_daily(trade_date)`: 支持大盘指数与申万行业指数采集。

### 2. 数据访问层 (shared/db/)

#### [MODIFY] [dao.py](file:///home/ubuntu/microservice-stock/scf-collector/shared/db/dao.py)
- 增加 `save_adj_factor(data)`: 写入 `stock_adjust_factor`。
- 增加 `save_industry_members(data)`: 写入 `dim_sw_industry_member`。
- 增加 `save_index_kline(data)`: 写入 `ods_index_daily` 或 `ods_sw_index_daily`。

### 3. 函数入口层 (functions/)

#### [MODIFY] [daily_quotes/index.py](file:///home/ubuntu/microservice-stock/scf-collector/functions/daily_quotes/index.py)
- 增加 `op=sync_kline_daily`: 批量采集全 A 日线。
- 增加 `op=sync_adj_factor`: 批量采集复权因子。

#### [MODIFY] [meta_sync/index.py](file:///home/ubuntu/microservice-stock/scf-collector/functions/meta_sync/index.py)
- 增加 `op=sync_sw_industry_member`: 同步申万行业成员维表。

## Verification Plan

### Automated Tests
- `pytest tests/scf_collector/test_s1_batch_sync.py`: 验证批量采集与入库的幂等性及量纲。
- 使用 `event = {"op": "sync_kline_daily", "trade_date": "2026-05-12"}` 触发本地模拟测试。

### Manual Verification
- 检查 `meta_data_readiness` 是否产生正确的 `READY` 信号。
- SQL 抽查 `stock_adjust_factor` 在除权日的数据跳变。
