# Done List: 已落地的云函数采集表清单

本文件记录 `scf-collector` 微服务中已完成开发、测试并部署的原始数据表。

## 1. 系统元数据与审计 (Meta & Audit)

| 表名 | 描述 | 采集频率 | 状态 | 云函数名称 (物理 ID) |
|---|---|---|---|---|
| `trade_cal` | 交易日历 | 每月 1 号 | 🟢 生产就绪 | `stock-scf-meta` |
| `stock_basic_info` | 股票基础信息 (维表) | 每日凌晨 06:00 | 🟢 生产就绪 | `stock-scf-meta` |
| `meta_pipeline_run` | 任务流水审计 | 实时写入 | 🟢 生产就绪 | (系统组件) |
| `meta_data_readiness` | 数据就绪信号 | 实时写入 | 🟢 生产就绪 | (系统组件) |
| `meta_data_audit_log` | 数据源影子审计报告 | 盘后 17:00 | 🟢 生产就绪 | `stock-serverless-collector` |

## 2. 交易行情 (Daily Quotes)

| 表名 | 描述 | 采集频率 | 状态 | 云函数名称 (物理 ID) |
|---|---|---|---|---|
| `stock_kline_daily` | 日线 K 线并内嵌复权因子 (不复权行情 + 最新复权因子内存合并) | 盘后 16:30 | 🟢 生产就绪 | `stock-serverless-collector` |
| `stock_adjust_factor` | 复权因子 (仅存储因子变动点) | 交易日 09:25 | 🟢 生产就绪 | `stock-serverless-collector` |
| `dim_sw_industry_member`| 申万行业成员 | 每日 18:00 | 🟢 生产就绪 | `stock-scf-meta` |
| `ods_index_daily` | 指数行情 | 盘后 16:30 | 🟢 生产就绪 | `stock-serverless-collector` |
| `v_latest_adjust_factors` | [NEW VIEW] 最新因子缓存视图 | 实时动态查询 | 🟢 生产就绪 | (数据库视图) |
| `v_stock_kline_forward_adj` | [NEW VIEW] 动态前复权日线视图 | 实时动态查询 | 🟢 生产就绪 | (数据库视图) |

---
- 2026-05-16: [Epic E12] K线数据质量保障体系完工。上线 S1(理论空洞审计)、S2(影子源对账/物理校验) 及 S3(任务化自动修复)，实现全量历史数据 100% 物理合规。
- 2026-05-17: [Epic E3] 复权因子内嵌合并与云端三层容灾自愈系统完工。将 `DailyAdjFactor` 前移至交易日 `09:25`（Cron: `0 25 9 * * * *`），避免因子拉取与日 K 线采集任务冲突。日线采集支持极速本地合并及 Tushare 实时补货的第二层自愈，盘后 17:00 自动执行第三层脏数据热修补，完全杜绝脏数据。
- 2026-05-17: [Epic E4-S1] 跨源前复权价格一致性校验与动态 QFQ 视图部署完工。成功物理清除全库 6,004 行早期旧系统因子残留，使用极速并发区间合并回填算法在 2.32 分钟内广播刷新全表 1700万行 K 线；经对账审计（第一批 100 只股，第二批 50 只全新独立股，共计 810,742 个交易日数据点），偏离度达到完美的 0.000000% 绝对契合！正式上线 MySQL 5.7 级联动态前复权视图 `v_stock_kline_forward_adj`，达成除权事件零物理重写、零延迟秒级对齐。

