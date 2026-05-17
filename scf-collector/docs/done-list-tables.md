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
| `stock_kline_daily` | 日线 K 线 (不复权) | 盘后 16:30 | 🟢 生产就绪 | `stock-serverless-collector` |
| `stock_adjust_factor` | 复权因子 | 盘后 16:30 | 🟢 生产就绪 | `stock-serverless-collector` |
| `dim_sw_industry_member`| 申万行业成员 | 每日 18:00 | 🟢 生产就绪 | `stock-scf-meta` |
| `ods_index_daily` | 指数行情 | 盘后 16:30 | 🟢 生产就绪 | `stock-serverless-collector` |

## 3. 政策与 AI 监控 (Policy & AI)

| 表名 | 描述 | 采集频率 | 状态 | 云函数名称 (物理 ID) |
|---|---|---|---|---|
| `ods_policy_info` | 政策原文数据表 | 实时/定期 (半小时) | 🟢 生产就绪 | `scf-policy-monitor` |

---
**更新记录**:
- 2026-05-17: [Epic E14-S1] 数据采集层建设。新建独立云函数 `scf-policy-monitor` 抓取多源 JSON/HTML 数据接口，入库 `ods_policy_info`，实现了 URL/MD5 双重去重，并完美对接了 ServerChan 微信通知与 SMTP 邮件警报。
- 2026-05-16: [Epic E12] K线数据质量保障体系完工。上线 S1(理论空洞审计)、S2(影子源对账/物理校验) 及 S3(任务化自动修复)，实现全量历史数据 100% 物理合规。
- 2026-05-16: [Epic E13-S2] 全市场 K 线源迁移。彻底废弃 BaoStock 源，完成 `stock_kline_daily` 清空并在云端服务器启动 Tushare 单线程全量回填，保障行情数据“不复权”纯净性。
- 2026-05-15: [Epic E400-S1] 复权因子内嵌...
- 2026-05-13: [Epic E8-S1] 复权因子存储重构...
- 2026-05-13: [Epic E7] 增强采集可靠性。已实现 S3 (字段契约强制) 及 S4 (完整性熔断与 AkShare 全量备份接管)，校验时点 17:00。
- 2026-05-12: 初始化清单，记录已上线的 5 张核心表。

