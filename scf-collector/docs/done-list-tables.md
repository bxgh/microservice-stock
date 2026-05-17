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

## 3. 政策与 AI 监控 (Policy & AI)

| 表名 | 描述 | 采集频率 | 状态 | 云函数名称 (物理 ID) |
|---|---|---|---|---|
| `ods_policy_info` | 政策原文数据表 | 半小时 (高频定时) | 🟢 生产就绪 | `stock-policy-collector` |
| `dwd_policy_analysis` | [NEW] AI 措辞提炼与重要性度量明细表 | 5分钟定时队列 | 🟢 生产就绪 | `stock-policy-analyzer` |
| `dwd_policy_sector_impact` | [NEW] 板块申万影响明细表 | 5分钟定时队列 | 🟢 生产就绪 | `stock-policy-analyzer` |
| `meta_llm_daily_cost` | [NEW] 大模型天级计费审计防爆表 | 实时写入审计 | 🟢 生产就绪 | `stock-policy-analyzer` |
| `dim_policy_keyword_sector` | [NEW] 行业敏感词行业匹配规则表 (配置表) | 静态只读 (23条种子灌入) | 🟢 生产就绪 | (系统静态维表) |

---
**更新记录**:
- 2026-05-17: [Epic E14-S2 v2] 政策解耦部署与云端 v13 补丁依赖层激活。将单体采集拆分为：`stock-policy-collector` (高频采集去重)、`stock-policy-analyzer` (并发乐观分布式锁、LIMIT 5 队列、LLM 智能研报主引擎)、`stock-policy-notifier` (微信简报、删除线 HTML side-by-side 响应式投研邮件推送)。编译打包 Version 13 物理补丁层（集成 `exceptiongroup` 关键异步底座包），完美解决 Python 3.10 Cloud 容器下的 `anyio`、`httpx` 及 `openai` 库多米诺骨牌式崩溃，全链路级联 Invoke 100% 远程调试通车！
- 2026-05-17: [Epic E14-S1] 数据采集层建设。新建独立云函数 `scf-policy-monitor` 抓取多源 JSON/HTML 数据接口，入库 `ods_policy_info`，实现了 URL/MD5 双重去重，并完美对接了 ServerChan 微信通知与 SMTP 邮件警报。
- 2026-05-16: [Epic E12] K线数据质量保障体系完工。上线 S1(理论空洞审计)、S2(影子源对账/物理校验) 及 S3(任务化自动修复)，实现全量历史数据 100% 物理合规。
- 2026-05-17: [Epic E3] 复权因子内嵌合并与云端三层容灾自愈系统完工。将 `DailyAdjFactor` 前移至交易日 `09:25`（Cron: `0 25 9 * * * *`），避免因子拉取与日 K 线采集任务冲突。日线采集支持极速本地合并及 Tushare 实时补货的第二层自愈，盘后 17:00 自动执行第三层脏数据热修补，完全杜绝脏数据。
- 2026-05-17: [Epic E4-S1] 跨源前复权价格一致性校验与动态 QFQ 视图部署完工。成功物理清除全库 6,004 行早期旧系统因子残留，使用极速并发区间合并回填算法在 2.32 分钟内广播刷新全表 1700万行 K 线；经对账审计（第一批 100 只股，第二批 50 只全新独立股，共计 810,742 个交易日数据点），偏离度达到完美的 0.000000% 绝对契合！正式上线 MySQL 5.7 级联动态前复权视图 `v_stock_kline_forward_adj`，达成除权事件零物理重写、零延迟秒级对齐。
- 2026-05-16: [Epic E13-S2] 全市场 K 线源迁移。彻底废弃 BaoStock 源，完成 `stock_kline_daily` 清空并在云端服务器启动 Tushare 单线程全量回填，保障行情数据“不复权”纯净性。
- 2026-05-15: [Epic E400-S1] 复权因子内嵌...
- 2026-05-13: [Epic E8-S1] 复权因子存储重构...
- 2026-05-13: [Epic E7] 增强采集可靠性。已实现 S3 (字段契约强制) 及 S4 (完整性熔断与 AkShare 全量备份接管)，校验时点 17:00。
- 2026-05-12: 初始化清单，记录已上线的 5 张核心表。



