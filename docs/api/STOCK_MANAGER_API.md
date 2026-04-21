# Stock-Manager 业务中台接口文档 (Stock-Manager API)

> **端口 (Port)**: 8004  
> **核心职能**: 多源数据同步调度、元数据管理、博弈/筹码记录持久化、监控评分查询。
> **⚠️ 重要提示**: 本服务 (8004) **不提供** K 线行情及估值数据的查询。如需 K 线数据，请调用 `BaoStock-API` (Port 8001)。
腾讯云ip: [IP_ADDRESS]  124.221.80.250
---

## 1. 基础元数据 (Fundamental & Metadata)
涉及标的基础信息、交易日历等核心字典数据。

| 接口路径 | 方法 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- |
| `/api/v1/metadata/baseline/current` | GET | **静态/统计** | 从 `stock-basic-info` 获取全市场 A 股标的总数及分类统计。 |
| `/api/v1/metadata/calendar/tradingDays` | GET | **时序/字典** | 从 `trade-calendar` 获取指定周期的交易日历。 |

---

## 2. 股东数据 (Shareholders)
涉及 `stock_shareholder_count` 和 `stock_shareholder_top10` 字表。

| 接口路径 | 方法 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- |
| `/api/v1/shareholders/count/{code}` | GET | **季度报告** | 获取个股历史股东户数及变化比例。 |
| `/api/v1/shareholders/top10/{code}` | GET | **季度报告** | 获取个股最近一期前十大自由流通股东明细。 |
| `/api/v1/shareholders/sync/{code}` | POST | **增量入库** | 手动触发单只股票的股东数据从源端同步至 MySQL。 |
| `/api/v1/shareholders/sync-batch` | POST | **批处理** | 批量同步多只股票的股东信息。 |

---

## 3. 财务报表 (Financial Reports)
涉及核心三大会计报表的历史记录。数据源自 AkShare (EM/Tushare) 并持久化于 MySQL。

| 接口路径 | 方法 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- |
| `/api/v1/finance/reports/{code}` | GET | **时序报表** | 获取个股历史三大会计报表（资产负债表、利润表、现金流量表）。支持 `limit` 参数控制返回的报告期数量。 |
| `/api/v1/finance/indicators/{code}` | GET | **衍生指标** | 获取个股历史财务衍生指标（ROE, ROA, 毛利率, 资产负债率, EPS等）。 |
| `/api/v1/finance/sync/{code}` | POST | **个股同步** | 触发特定个股的历史财务报表从数据源完整同步至本地 MySQL。 |
| `/api/v1/finance/sync-indicators/{code}` | POST | **个股指标同步** | 触发特定个股的历史财务衍生指标同步，确保“盈利锚”引擎计算准确。 |
| `/api/v1/finance/sync-all-indicators` | POST | **全市场同步** | **[后台]** 触发全市场所有在市标的的财务衍生指标增量同步。建议每周执行。 |

---

## 4. 博弈与资金 (Game & Capital Flow)
涉及龙虎榜 (`stock_lhb_daily`) 和北向资金 (`stock_north_funds_daily`)。

| 接口路径 | 方法 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- |
| `/api/v1/game/lhb/{code}` | GET | **时序记录** | 查询个股历史龙虎榜成交记录（含机构买卖额）。 |
| `/api/v1/game/north/{code}` | GET | **时序指标** | 查询个股北向资金历史持股数量及占比波动。 |
| `/api/v1/game/sync/lhb` | POST | **每日增量** | 将全市场龙虎榜明细数据持久化到 MySQL。 |
| `/api/v1/game/sync/north` | POST | **每日增量** | 将每日北向资金持仓快照同步至 MySQL。 |
| `/api/v1/game/sync/north/history/{code}` | POST | **补全入库** | 补全特定标的历史北向持仓变化。 |

---

## 4. 筹码与供给 (Chips & Supply)
| `/api/v1/chips/restricted/{code}` | GET | **计划/事件** | 查询个股未来 60 天及历史的限售解禁计划。 |
| `/api/v1/chips/block_trade/{code}` | GET | **时序记录** | 记录个股成交价、成交额等大宗交易细节。 |
| `/api/v1/chips/sync/restricted` | POST | **增量更新** | 增量抓取全市场限售解禁信息并存入 MySQL。 |
| `/api/v1/chips/sync/block_trade` | POST | **增量更新** | 批量或单日同步全市场大宗交易记录。 |

---

## 5. 信息与舆情 (Information & Sentiment)
| 接口路径 | 方法 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- |
| `/api/v1/information/analyst-ranks/{code}` | GET | **评级记录** | 获取各机构对标的的评级历史（买入/增持等）。 |
| `/api/v1/information/forecasts/{code}` | GET | **季度报告** | 获取公司发布的季度/年度业绩预告细节。 |
| `/api/v1/information/sentiment/{code}` | GET | **每日状态** | 查询每日市场热度分布与排名得分情况。 |
| `/api/v1/information/analyst-ranks/sync` | POST | **当日同步** | 同步最新当日分析师研报数据。 |
| `/api/v1/information/analyst-ranks/sync-fetch` | POST | **深度同步** | **[强制]** 从源端重新全量拉取机构评级数据。 |
| `/api/v1/information/forecasts/sync` | POST | **当日同步** | 抓取最新当日业绩预告并持久化入库。 |
| `/api/v1/information/forecasts/sync-fetch` | POST | **深度同步** | **[强制]** 从源端重新全量拉取业绩预告数据。 |
| `/api/v1/information/sentiment/sync` | POST | **当日同步** | 同步当日全市场热度评分。 |
| `/api/v1/information/sentiment/sync-fetch/{code}` | POST | **深度同步** | **[强制]** 重新拉取指定个股的深度热度数据。 |

---

## 6. 监控与评分 (Monitor & Scores)
涉及综合健康分 (`monitor_scores`) 和各项子统计。

| 接口路径 | 方法 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- |
| `/api/v1/monitor/summary` | GET | **聚合统计** | 计算并返回当前高分标的占比、入库进度等概览指标。 |
| `/api/v1/monitor/history/score` | GET | **时序曲线** | 查询全市场监控得分的历史连续变动，用于绘图。 |
| `/api/v1/monitor/history/indicator/{name}` | GET | **分项统计** | 查询特定监控指标（如 LHB 热度）的历史变动。 |

---

## 7. 运维与审计 (Ops & Audit)
| 接口路径 | 方法 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- |
| `/api/v1/ops/freshness` | GET | **状态概览** | 检测 MySQL 中各大核心表的同步刷新时间，判断滞后情况。 |
| `/api/v1/ops/adjust-factor` | GET | **核查数据** | 返回指定日期的全市场复权因子“覆盖统计”，不返回序列数据。 |
| `/api/v1/audit/weekly` | GET | **审计报告** | 汇总最近一周的同步执行记录，生成完整性报告。 |
| `/api/v1/data-audits` | GET | **日志记录** | 列出所有的静态数据/动态数据一致性核查记录。 |

---

## 8. 指令与任务流 (Commands & Tasks)
线上存在两套平行的指令控制机制。

### 8.1 即时指令 (Simple Commands)
用于下达触发简单的、即时反馈的后台同步操作。

| 接口路径 | 方法 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- |
| `/api/v1/commands` | GET | **日志** | 查阅所有已下达的即时指令记录。 |
| `/api/v1/commands` | POST | **指令写入** | 下达一个即时同步指令（如：`daily_kline_sync`）。 |
| `/api/v1/commands/{id}` | GET | **状态** | 获取特定指令的执行进度。 |

### 8.2 长效任务流 (Task Commands)
用于管理涉及多步操作或长审计周期的高阶异步任务。

| 接口路径 | 方法 | 数据性质 | 说明 |
| :--- | :--- | :--- | :--- |
| `/api/v1/task-commands` | GET | **任务日志** | 获取所有下达的长效异步指令执行记录。 |
| `/api/v1/task-commands` | POST | **任务写入** | 下达一个新的异步任务指令。 |
| `/api/v1/task-commands/{id}` | GET | **状态细节** | 查看长效任务的实时原子日志。 |

---

## 9. 数据库表映射参考 (Appendix)
*   **基础**: `stock-basic-info`, `trade-calendar`
*   **财务**: `stock-balance-sheet`, `stock-income-statement`, `stock-cash-flow-statement`, `stock-finance-indicators`
*   **行情**: `stock-kline-daily`, `stock-valuation-daily` (**注：仅供后台同步，8004 不对外提供查询**)
*   **博弈**: `stock-lhb-daily`, `stock-north-funds-daily`
*   **股东**: `stock-shareholder-count`, `stock-shareholder-top10`
*   **筹码**: `stock-block-trade`, `stock-restricted-release`
*   **监控**: `monitor-scores`, `monitor-indicators`
*   **系统**: `task-commands`, `ops-audit-logs`, `sync-progress`
