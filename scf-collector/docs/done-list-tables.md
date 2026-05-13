# Done List: 已落地的云函数采集表清单

本文件记录 `scf-collector` 微服务中已完成开发、测试并部署的原始数据表。

## 1. 系统元数据与审计 (Meta & Audit)

| 表名 | 描述 | 采集频率 | 状态 | 云函数名称 (物理 ID) |
|---|---|---|---|---|
| `trade_cal` | 交易日历 | 每月 1 号 | 🟢 生产就绪 | `stock-scf-meta` |
| `stock_basic_info` | 股票基础信息 (维表) | 每日凌晨 06:00 | 🟢 生产就绪 | `stock-scf-meta` |
| `meta_pipeline_run` | 任务流水审计 | 实时写入 | 🟢 生产就绪 | (系统组件) |
| `meta_data_readiness` | 数据就绪信号 | 实时写入 | 🟢 生产就绪 | (系统组件) |
| `meta_data_audit_log` | 数据源影子审计报告 | 盘后 16:30 | 🟢 生产就绪 | `stock-serverless-collector` |

## 2. 交易行情 (Daily Quotes)

| 表名 | 描述 | 采集频率 | 状态 | 云函数名称 (物理 ID) |
|---|---|---|---|---|
| `stock_kline_daily` | 日线 K 线 (不复权) | 盘后 16:30 | 🟢 生产就绪 | `stock-serverless-collector` |
| `stock_adjust_factor` | 复权因子 | 盘后 16:30 | 🟢 生产就绪 | `stock-serverless-collector` |
| `dim_sw_industry_member`| 申万行业成员 | 每日 18:00 | 🟢 生产就绪 | `stock-scf-meta` |
| `ods_index_daily` | 指数行情 | 盘后 16:30 | 🟢 生产就绪 | `stock-serverless-collector` |

---
**更新记录**:
- 2026-05-12: 初始化清单，记录已上线的 5 张核心表。
