# 微服务股票数据系统 - 定时任务部署清单 (2026-05-03)

## 1. 调度架构综述

项目采用**分布式本地调度**模式：
- **核心组件**: 基于 `APScheduler` (AsyncIOScheduler)。
- **分布状态**: 
  - `stock-manager`: 业务中台调度，负责逻辑聚合与跨服务触发。
  - `akshare-api`: 数据源端调度，负责财务、板块、元数据等抓取。
  - `baostock-api`: 数据源端调度，负责 K 线数据的可用性轮询。
  - `pywencai-api`: 仅保留心跳任务。
- **管理接口**: `stock-manager` 聚合了所有容器的任务，可通过 `GET /api/v1/scheduler/jobs` 统一查看。

---

## 2. 任务清单 (按时间线)

### 2.1 凌晨/早盘 (数据同步与盘前准备)
| 执行时间 | 任务 ID | 所属服务 | 功能描述 |
| :--- | :--- | :--- | :--- |
| 02:00 (周六) | `weekly_metadata_sync` | akshare | 同步全市场基础元数据 |
| 02:30 | `daily_finance_indicators_sync` | stock-manager | 同步全市场财务衍生指标 |
| 03:00 | `daily_analyst_rating_sync` | stock-manager | 同步机构评级数据 (Tushare) |
| 04:00 | `daily_shareholder_sync` | stock-manager | 同步股东数据 (Tushare) |
| 08:45 | `daily_performance_forecast_sync` | stock-manager | **[盘前]** 同步当日业绩预告 |
| 09:15 | `daily_suspension_morning_sync` | stock-manager | **[盘前]** 同步当日停复牌清单 |

### 2.2 盘中与收盘初期 (状态监控与初步采集)
| 执行时间 | 任务 ID | 所属服务 | 功能描述 |
| :--- | :--- | :--- | :--- |
| 每 1 小时 | `health_check` | baostock | BaoStock 连接状态与系统健康自检 |
| 每 1 小时 | `akshare_heartbeat` | akshare | 调度器活跃心跳 |
| 15:30 | `daily_monitor_data_sync` | stock-manager | **[收盘]** 触发 monitor-service 同步资金面数据 |
| 15:45 | `daily_monitor_calculate` | stock-manager | **[收盘]** 触发 monitor-service 执行指标计算与评分 |
| 17:00-23:00 (每15m) | `daily_kline_watcher` | baostock | 监测交易所 K 线数据发布情况 |
| 17:30 | `daily_etf_kline_sync` | akshare | 同步 ETF 基金行情数据 |

### 2.3 晚盘 (核心流水线)
| 执行时间 | 任务 ID | 所属服务 | 功能描述 |
| :--- | :--- | :--- | :--- |
| 19:00 | `daily_market_data_sync` | akshare | 同步市场综合行情 (AkShare 源) |
| 19:15 | `daily_l2_structural_sync` | akshare | 同步 L2 结构化分化指标 (ADS 层) |
| 19:30 | `daily_market_overview_sync` | stock-manager | **核心流水线**: 指数、K线(双源)、广度、L1/L2全景计算 |
| 19:45 | `daily_sentiment_sync` | akshare | 同步当日市场情绪指标 |
| 20:00 | `daily_financial_incremental_sync` | akshare | 增量同步当日最新财务报表 |

### 2.4 周末维护 (全量校准)
| 执行时间 | 任务 ID | 所属服务 | 功能描述 |
| :--- | :--- | :--- | :--- |
| 01:00 (周六) | `weekly_stock_list_sync` | akshare | 校准全市场股票清单 |
| 03:00 (周六) | `weekly_ths_sector_sync` | akshare | 同步同花顺板块/行业成分 |
| 04:00 (周六) | `weekly_restricted_release` | akshare | 同步次周限售股解禁计划 |
| 05:00 (周六) | `weekly_financial_report_sync` | akshare | 全量校准本季财务数据 |

---

## 3. 核心流水线细节说明

### 3.1 `daily_market_overview_sync` (主任务)
该任务是系统的“每日总结”，在 `stock-manager` 中运行，逻辑如下：
1. **指数同步**: 优先从 Tushare 获取核心指数。
2. **K线同步**: 采用 **Tushare 优先 + BaoStock 兜底** 策略。
3. **涨跌停池**: 从 AkShare 获取。
4. **计算环节**: 自动触发市场广度、L1 全景及 L2 完整指标计算。

### 3.2 任务触发关系
- **主动触发**: `stock-manager` -> `monitor-service` (通过 HTTP API `/api/v1/sync/daily`)。
- **数据依赖**: 多数 L2 指数计算依赖于 `akshare-api` 完成 ODS 层数据抓取。

---

## 4. 运行状态与已知问题 (2026-05-03 巡检)

### 4.1 任务执行记录 (近期)
- `daily_suspension_morning_sync`: **SUCCESS** (2026-05-03 09:15)
- `daily_performance_forecast_sync`: **SUCCESS** (2026-05-03 08:45)
- `daily_market_overview_sync`: **FAILED** (2026-05-02 19:30)
  - **错误原因**: `IndicatorService` 计算 L2 指标时 SQL 参数不匹配。
  - **影响范围**: ADS 层行业/概念/风格因子指标未生成。
- `daily_analyst_rating_sync`: **SUCCESS** (2026-05-03 03:00)

### 4.2 技术债务与修复计划
- **[DONE] 修复 L2 指标计算异常**: 已修复 `indicator_service.py` 中的 SQL 参数匹配问题。
- **[P1] Broken Pipe 自动重连**: `baostock-api` 在长连接断开后需确保 `_ensure_connection` 逻辑覆盖所有入口。
- **[P2] 日志集中化**: 当前日志分散在各容器内部，建议挂载宿主机目录或集成 ELK/Loki。

---

## 5. 注意事项
- **时区**: 所有时间均为 `Asia/Shanghai`。
- **重试机制**: `stock-manager` 的调度器支持 `max_instances=1` 和 `replace_existing=True`，防止任务堆积。
- **监控**: 建议定期检查 `stock-manager` 的 `logs/app.log` 以识别 API 额度超限错误。
