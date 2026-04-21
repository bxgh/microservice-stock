# 静态数据库 (MySQL) 交互接口指南 (Static DB API Guide)

> **版本**: 1.0  
> **状态**: 已整理  
> **说明**: 本文档专门汇总了直接操作、同步或查询云端 MySQL 数据库（`alwaysup` 库）的 API 接口。
腾讯云ip: [IP_ADDRESS]  124.221.80.250
---

## 1. 基础元数据 (Fundamental & Metadata)
此类数据存储在 `stock_basic_info` (标的信息)、`trade_calendar` (交易日历) 等表中，是系统的基石。

| 接口路径 | 方法 | 服务 | 端口 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/metadata/baseline/current` | GET | Stock-Manager | 8004 | **静态/统计** | 获取当前 MySQL 中录入的所有 A 股标的总数及分板块统计。 |
| `/api/v1/metadata/calendar/tradingDays` | GET | Stock-Manager | 8004 | **时序/字典** | 获取交易日历，用于确定数据抓取和计算的时间基准。 |
| `/api/v1/metadata/sync/stock-list` | POST | AkShare-API | 8003 | **全量同步** | 触发将全市场股票基础信息从数据源同步至 MySQL `stock_basic_info` 表。 |
| `/api/v1/metadata/sync/sw-industries` | POST | AkShare-API | 8003 | **关系数据** | 同步申万行业分类数据。 |
| `/api/v1/metadata/sync/issue-prices` | POST | AkShare-API | 8003 | **静态数据** | 同步个股发行价数据，用于发行价破位计算。 |

---

## 2. 股东与机构数据 (Shareholders & Institutional)
存储在 `stock_shareholder_count` 和 `stock_shareholder_top10` 等表中。

| 接口路径 | 方法 | 服务 | 端口 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/shareholders/count/{code}` | GET | Stock-Manager | 8004 | **季度报告** | 获取个股的历史股东户数变化情况。 |
| `/api/v1/shareholders/top10/{code}` | GET | Stock-Manager | 8004 | **季度报告** | 获取个股前十大股东明细。 |
| `/api/v1/shareholders/sync/{code}` | POST | Stock-Manager | 8004 | **增量入库** | 针对特定股票触发股东数据的抓取并持久化至 MySQL。 |

---

## 3. 财务报表数据 (Financial Reports)
涉及 `stock_balance_sheet` (资产负债表)、`stock_income_statement` (利润表) 和 `stock_cash_flow_statement` (现金流量表)。

| 接口路径 | 方法 | 服务 | 端口 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/finance/reports/{code}` | GET | Stock-Manager | 8004 | **时序报表** | 获取个股历史三大会计报表数据的结构化 JSON。 |
| `/api/v1/finance/indicators/{code}` | GET | Stock-Manager | 8004 | **衍生指标** | 获取个股历史财务衍生指标（ROE, EPS 等）。 |
| `/api/v1/finance/sync/{code}` | POST | Stock-Manager | 8004 | **全量同步** | 从数据源抓取个股全量历史财务报表并增量存入 MySQL。 |
| `/api/v1/finance/sync-indicators/{code}` | POST | Stock-Manager | 8004 | **指标同步** | 同步个股历史财务衍生指标数据。 |

---

## 4. 行情同步与持久化 (Market Data Persistence)
涉及到 `stock_daily_kline` (日线)、`stock_valuation_daily` (估值) 等核心大表。

| 接口路径 | 方法 | 服务 | 端口 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/sync/full` | POST | BaoStock-API | 8001 | **批处理同步** | 全市场 A 股 K 线数据的自动化增量同步至 MySQL。 |
| `/api/v1/sync/status` | GET | BaoStock-API | 8001 | **运维状态** | 查询当前 MySQL K 线同步任务的进度和汇总统计。 |
| `/api/v1/sync/freshness` | GET | BaoStock-API | 8001 | **数据审计** | 检测 MySQL 中各表数据的最新时间戳，判断是否存在数漏。 |
| `/api/v1/game/sync/lhb` | POST | Stock-Manager | 8004 | **每日增量** | 将龙虎榜 (LHB) 每日明细数据同步至 MySQL。 |
| `/api/v1/game/sync/north` | POST | Stock-Manager | 8004 | **每日增量** | 将北向资金持仓数据同步至 MySQL。 |

---

## 4. 停牌与业绩数据 (Events & Performance)
存储在 `stock_suspension` (停牌) 和 `stock_performance_forecast` (业绩预告) 等表中。

| 接口路径 | 方法 | 服务 | 端口 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/suspensions/sync` | POST | Stock-Manager | 8004 | **每日状态** | 抓取今日停牌数据并更新至 MySQL，用于排除计算标的。 |
| `/api/v1/information/forecasts/sync` | POST | Stock-Manager | 8004 | **公告数据** | 同步业绩预告数据，用于信息维度评分。 |

---

## 5. 计算指标与监控评分 (Monitoring & Scores)
核心存储在 `monitor_scores` (综合分) 和 `monitor_indicators` (分项指标) 中。

| 接口路径 | 方法 | 服务 | 端口 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/monitor/summary` | GET | Stock-Manager | 8004 | **聚合分析** | 从 MySQL 读取全市场最新的监控指标汇总（如高分占比等）。 |
| `/api/v1/monitor/history/score` | GET | Stock-Manager | 8004 | **时序指标** | 查询特定标的历史健康度评分曲线。 |
| `/api/v1/calculate` | POST | Monitor-Service | 8006 | **引擎入库** | 触发评分引擎计算并将结果持久化到 MySQL `monitor_scores` 表。 |

---

## 6. 系统与审计 (System & Audit)
存储在 `ops_audit_logs` (审计日志)、`task_executions` (任务执行) 等表中。

| 接口路径 | 方法 | 服务 | 端口 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/audit/weekly` | GET | Stock-Manager | 8004 | **分析报告** | 汇总 MySQL 中的同步日志，生成周度数据质量审计报告。 |
| `/api/v1/data-audits` | GET | Stock-Manager | 8004 | **质量报告** | 查询 MySQL 中记录的数据一致性核查结果。 |
| `/api/v1/commands` | GET/POST | Stock-Manager | 8004 | **交互日志** | 管理和记录所有对数据库产生变更的手动干预命令。 |

---

## 数据性质说明指南
*   **静态/词典**: 变更频率极低（如行业定义、发行价）。
*   **时序/K线**: 每日收盘后产生一批（如日线行情、每日评分）。
*   **状态/看板**: 描述当前系统或市场的瞬时情况（如今日停牌、同步状态）。
*   **月度/季度**: 随定期报告发布，更新周期长（如股东人数、业绩预告、三大会计报表）。
*   **审计/日志**: 记录系统行为的历史足迹。
