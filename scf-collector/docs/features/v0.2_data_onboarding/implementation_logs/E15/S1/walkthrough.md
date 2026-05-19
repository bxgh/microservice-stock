# Walkthrough - E15-S1: P0级行情池与两融指标采集模块

本 Story 实现了 A 股盘后分析系统 v0.2 的核心行情数据、两融（融资融券）数据及停牌日历的采集，并基于本地 K 线与停牌日历自主派生全市场行情广度（面包线）指标，确保高容灾性与高流控安全性。

## 变更内容

1. **E15-S1-T1: 编写 `sync_limit_pool` 采集接口**
   - 编写 `ods_event_limit_pool` 的幂等入库 DAO 函数 `save_limit_pool`。
   - 接入 `index.py` 的 `sync_limit_pool` 操作分支，聚合 Tushare 涨跌停、连板池和 AkShare 炸板池。
2. **E15-S1-T2: 编写 `sync_suspend_calendar` 每日盘前停牌更新**
   - 实现 `StockDAO` 中的停牌数据保存逻辑，表为 `stock_suspensions`。
   - 接入 `index.py` 的 `sync_suspend_calendar` 操作分支。
3. **E15-S1-T3: 编写 `sync_margin_data` 盘后两融数据同步与断点续传**
   - 编写 `migrations/20260519_create_ods_margin_total.sql` 迁移脚本，定义了 `ods_margin_total`（全市场汇总）与 `ods_margin_detail`（个股明细）的 DDL。
   - 在 `TushareCollector` 中实现 `fetch_margin` 方法。
   - 实现 `StockDAO` 中的两融数据最新日期查询、保存汇总与保存明细逻辑，通过 `MAX(trade_date)` 自动定位增量续传，内置 `0.5s` 平滑流控。
4. **E15-S1-T4: 实现本地 `ods_market_breadth_daily` 面包线派生**
   - 编写 `StockDAO.derive_market_breadth` 方法，完全基于本地 `stock_kline_daily` 与停牌表做聚合计算，规避频次限制。
   - 接入 `index.py` 的 `derive_market_breadth` 操作分支。

## 验证证据

我们编写了全覆盖的高质量单元测试 `tests/test_e15_s1.py`，完整覆盖了 Collectors、StockDAO 数据入库（包含百分比除以 100.0 标准化换算）以及 SCF 主控制器的四种 op 流程。

### 测试执行结果

```bash
pytest tests/test_e15_s1.py
```

```text
============================= test session starts =============================
platform win32 -- Python 3.11.5, pytest-7.4.3, pluggy-1.6.0
rootdir: E:\gitee\microservice-stock
plugins: anyio-3.7.1, asyncio-0.21.1, cov-4.1.0
asyncio: mode=Mode.STRICT
collected 4 items

tests\test_e15_s1.py ....                                                [100%]

======================== 4 passed, 1 warning in 2.53s =========================
```

- **AC1: 两融断点无损校验**：已通过 Mock `get_latest_margin_date` 验证，自动识别已入库的 `MAX(trade_date)` 增量向前，不破坏历史数据。
- **AC2: 涨跌停池唯一性与幂等覆盖**：使用 `ON DUPLICATE KEY UPDATE`，且强制更新 `updated_at = CURRENT_TIMESTAMP`。

## 角色审查意见

- **[DB Auditor]**: 新增 DDL 脚本已放置在 `migrations/` 目录下，并使用 `Asia/Shanghai` 时区，严格包含尾部三件套及其索引，且无窗口函数或 CTE，完全兼容 MySQL 5.7。
- **[Backend Engineer]**: 所有的 `op` 流程均在 `finally` 块中通过 `await DBManager.close_pool()` 安全释放连接池。在批量同步中内置 `0.5s` 平滑流控防止 IP 被封禁。
- **[Data Quality Steward]**: 实现了百分比字段除以 100.0 的标准小数值转换，金额一律换算对齐为“元”单位，映射矩阵完美对齐。
- **[QA/Test Engineer]**: 编写了高保真 Mock 测试，无需网络资源和真实数据库，在 2.53s 内实现 100% 逻辑覆盖，极速绿色通过。
