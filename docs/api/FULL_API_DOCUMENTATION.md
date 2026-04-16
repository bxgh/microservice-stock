# 股票微服务集群 API 接口文档汇总

> **生成时间**: 2026-04-17 00:11:14
> **状态**: 自动从当前运行容器提取

## Stock-Manager (http://127.0.0.1:8004)

| 接口路径 | 方法 | 摘要 | 标签 |
| :--- | :--- | :--- | :--- |
| `/api/v1/audit/gate` | GET | Get Gate Audits | 审计 |
| `/api/v1/audit/weekly` | GET | Get Audit Weekly | 审计 |
| `/api/v1/chips/block_trade/{code}` | GET | Get Block Trade | 筹码维度同步 |
| `/api/v1/chips/restricted/{code}` | GET | Get Restricted Release | 筹码维度同步 |
| `/api/v1/chips/sync/block_trade` | POST | Sync Block Trade | 筹码维度同步 |
| `/api/v1/chips/sync/restricted` | POST | Sync Restricted Release | 筹码维度同步 |
| `/api/v1/commands` | GET | List Commands | 命令 |
| `/api/v1/commands` | POST | Trigger Command | 命令 |
| `/api/v1/commands/{command_id}` | GET | Get Command Status | 命令 |
| `/api/v1/dashboard/overview` | GET | Get Overview | 仪表盘 |
| `/api/v1/data-audits` | GET | List Data Audits | 数据审计 |
| `/api/v1/data-audits/{id}` | GET | Get Data Audit Summary | 数据审计 |
| `/api/v1/data-audits/{id}/details` | GET | Get Data Audit Details | 数据审计 |
| `/api/v1/game/lhb/{code}` | GET | Get Lhb History | 博弈维度同步 |
| `/api/v1/game/north/{code}` | GET | Get North History | 博弈维度同步 |
| `/api/v1/game/sync/lhb` | POST | Sync Lhb | 博弈维度同步 |
| `/api/v1/game/sync/north` | POST | Sync North | 博弈维度同步 |
| `/api/v1/game/sync/north/history/{code}` | POST | Sync North History | 博弈维度同步 |
| `/api/v1/information/analyst-ranks/sync` | POST | Sync Analyst Ranks | 信息维度同步 |
| `/api/v1/information/analyst-ranks/sync-fetch` | POST | Sync Analyst Ranks From Src | 信息维度同步 |
| `/api/v1/information/analyst-ranks/{code}` | GET | Get Analyst Ranks | 信息维度同步 |
| `/api/v1/information/forecasts/sync` | POST | Sync Forecasts | 信息维度同步 |
| `/api/v1/information/forecasts/sync-fetch` | POST | Sync Forecasts From Src | 信息维度同步 |
| `/api/v1/information/forecasts/{code}` | GET | Get Forecasts | 信息维度同步 |
| `/api/v1/information/sentiment/sync` | POST | Sync Sentiment | 信息维度同步 |
| `/api/v1/information/sentiment/sync-fetch/{code}` | POST | Sync Sentiment From Src | 信息维度同步 |
| `/api/v1/information/sentiment/{code}` | GET | Get Sentiment | 信息维度同步 |
| `/api/v1/metadata/baseline/current` | GET | Get Current Baseline | 元数据 |
| `/api/v1/metadata/calendar/tradingDays` | GET | Get Trading Days | 元数据 |
| `/api/v1/monitor/history/indicator/{name}` | GET | Get Indicator History | 监控指标 |
| `/api/v1/monitor/history/score` | GET | Get Score History | 监控指标 |
| `/api/v1/monitor/summary` | GET | Get Monitor Summary | 监控指标 |
| `/api/v1/ops/adjust-factor` | GET | Get Adjust Factor By Date | 运维 |
| `/api/v1/ops/freshness` | GET | Get Sync Freshness | 运维 |
| `/api/v1/ops/remediate` | POST | Remediate Data | 运维 |
| `/api/v1/scheduler/jobs` | GET | Get All Jobs | 调度 |
| `/api/v1/scheduler/jobs/{job_id}/logs` | GET | Get Job Logs | 调度 |
| `/api/v1/scheduler/jobs/{job_id}/{action}` | POST | Control Job | 调度 |
| `/api/v1/scheduler/tasks` | GET | Get Tasks | 调度, 任务 |
| `/api/v1/shareholders/count/{code}` | GET | Get Holder Count | 股东数据 |
| `/api/v1/shareholders/sync-batch` | POST | Sync Batch Shareholder Data | 股东数据 |
| `/api/v1/shareholders/sync/{code}` | POST | Sync Shareholder Data | 股东数据 |
| `/api/v1/shareholders/top10/{code}` | GET | Get Top10 Holders | 股东数据 |
| `/api/v1/suspensions/sync` | POST | Sync Suspensions | 停牌数据 |
| `/api/v1/system/health` | GET | Health Check | 系统 |
| `/api/v1/task-commands` | GET | 获取指令列表 | 任务指令 |
| `/api/v1/task-commands` | POST | 下达任务指令 | 任务指令 |
| `/api/v1/task-commands/{command_id}` | GET | 查看指令状态 | 任务指令 |
| `/health` | GET | Health Check | - |

## AkShare-API (http://127.0.0.1:8003)

| 接口路径 | 方法 | 摘要 | 标签 |
| :--- | :--- | :--- | :--- |
| `/api/v1/block_trade/daily` | GET | Get Block Trade | 市场数据 |
| `/api/v1/capital_flow/{code}` | GET | Get Capital Flow | 市场数据 |
| `/api/v1/dividend/{code}` | GET | Get Dividend | 财务数据 |
| `/api/v1/dragon_tiger/daily` | GET | Get Dragon Tiger Daily | 市场数据 |
| `/api/v1/dragon_tiger/institution` | GET | Get Dragon Tiger Inst | 市场数据 |
| `/api/v1/finance/indicators/{code}` | GET | Get Finance Indicators | 财务数据 |
| `/api/v1/finance/{code}` | GET | Get Finance | 财务数据 |
| `/api/v1/forecast` | GET | Get Forecast Data | 财务数据 |
| `/api/v1/fund/etf_daily` | GET | Get Etf Daily | 市场数据 |
| `/api/v1/index/daily` | GET | Get Index Daily | 市场数据 |
| `/api/v1/index/sw_daily` | GET | Get Sw Index Daily | 市场数据 |
| `/api/v1/index/us_daily` | GET | Get Us Index Daily | 市场数据 |
| `/api/v1/industry/stock/{code}` | GET | Get Stock Industry | 市场数据 |
| `/api/v1/information/analyst-ranks` | GET | Get Analyst Ranks | 信息维度 |
| `/api/v1/information/forecasts` | GET | Get Forecasts | 信息维度 |
| `/api/v1/information/sentiment/{code}` | GET | Get Sentiment | 信息维度 |
| `/api/v1/margin/summary` | GET | Get Margin Summary | 市场数据 |
| `/api/v1/margin/{code}` | GET | Get Margin Data | 市场数据 |
| `/api/v1/market/breadth` | GET | Get Market Breadth | 市场数据 |
| `/api/v1/metadata/sync/all` | POST | Sync All Data | 元数据管理 |
| `/api/v1/metadata/sync/em-industries` | POST | Sync Em Industries | 元数据管理 |
| `/api/v1/metadata/sync/issue-prices` | POST | Sync Issue Prices | 元数据管理 |
| `/api/v1/metadata/sync/stock-list` | POST | Sync Stock List | 元数据管理 |
| `/api/v1/metadata/sync/sw-industries` | POST | Sync Sw Industries | 元数据管理 |
| `/api/v1/metadata/sync/ths-industries` | POST | Sync Ths Industries | 元数据管理 |
| `/api/v1/north/daily` | GET | Get North Funds Daily | 市场数据 |
| `/api/v1/north/flow_summary` | GET | Get North Flow Summary | 市场数据 |
| `/api/v1/north/history/{code}` | GET | Get North Funds History | 市场数据 |
| `/api/v1/rank/hot` | GET | Get Hot Rank | 市场数据 |
| `/api/v1/restricted/release` | GET | Get Restricted Release | 市场数据 |
| `/api/v1/scheduler/jobs` | GET | List Jobs | 任务调度 |
| `/api/v1/scheduler/jobs/{job_id}/logs` | GET | Get Job Logs | 任务调度 |
| `/api/v1/scheduler/jobs/{job_id}/pause` | POST | Pause Job | 任务调度 |
| `/api/v1/scheduler/jobs/{job_id}/resume` | POST | Resume Job | 任务调度 |
| `/api/v1/scheduler/jobs/{job_id}/run` | POST | Run Job | 任务调度 |
| `/api/v1/shareholder/{code}` | GET | Get Shareholder | 财务数据 |
| `/api/v1/suspension/daily` | GET | Get Suspension Daily | 市场数据 |
| `/api/v1/valuation/{code}` | GET | Get Valuation | 财务数据 |
| `/health` | GET | Health Check | - |

## BaoStock-API (http://127.0.0.1:8001)

| 接口路径 | 方法 | 摘要 | 标签 |
| :--- | :--- | :--- | :--- |
| `/api/v1/collect/batch` | POST | Batch Collect | 远程修复 |
| `/api/v1/collect/stock_history` | POST | Collect Stock History | 远程修复 |
| `/api/v1/collect/task/{task_id}` | GET | Get Collection Task Status | 远程修复 |
| `/api/v1/finance/profit/{code}` | GET | Get Profit Data | 指数与行业 |
| `/api/v1/history/kline/{code}` | GET | Get History Kline | K线数据 |
| `/api/v1/index/cons/{index}` | GET | Get Index Constituents | 指数与行业 |
| `/api/v1/industry/classify` | GET | Get Industry Classify | 指数与行业 |
| `/api/v1/logs/execution` | GET | List Execution Logs | 执行日志 |
| `/api/v1/market/stocks` | GET | Get Market Stocks | 市场数据 |
| `/api/v1/scheduler/jobs` | GET | List Jobs | 任务调度 |
| `/api/v1/scheduler/jobs/{job_id}/logs` | GET | Get Job Logs | 任务调度 |
| `/api/v1/scheduler/jobs/{job_id}/{action}` | POST | Handle Job Action | 任务调度 |
| `/api/v1/sync/adjust_factor/full` | POST | Sync Full Market Adjust Factor | 数据同步 |
| `/api/v1/sync/adjust_factor/status` | GET | Get Adjust Sync Status | 数据同步 |
| `/api/v1/sync/adjust_factor/{code}` | POST | Sync Stock Adjust Factor | 数据同步 |
| `/api/v1/sync/freshness` | GET | Get Sync Freshness | 数据同步 |
| `/api/v1/sync/full` | POST | Sync Full Market | 数据同步 |
| `/api/v1/sync/kline/{code}` | POST | Sync Stock Kline | 数据同步 |
| `/api/v1/sync/remediate` | POST | Post Sync Remediate | 数据同步 |
| `/api/v1/sync/reset` | POST | Reset Sync Progress | 数据同步 |
| `/api/v1/sync/run_pipeline` | POST | Run Sync Pipeline | 数据同步 |
| `/api/v1/sync/status` | GET | Get Sync Status | 数据同步 |
| `/api/v1/sync/verify/daily` | GET | Verify Daily Sync | 数据同步 |
| `/api/v1/sync/verify/weekly` | GET | Verify Weekly Sync | 数据同步 |
| `/api/v1/valuation/{code}/history` | GET | Get Valuation History | 估值数据 |
| `/health` | GET | Health Check | - |

## PyWencai-API (http://127.0.0.1:8002)

| 接口路径 | 方法 | 摘要 | 标签 |
| :--- | :--- | :--- | :--- |
| `/api/v1/query` | POST | Wencai Query | 问财查询 |
| `/api/v1/scheduler/jobs` | GET | List Jobs | 任务调度 |
| `/api/v1/scheduler/jobs/{job_id}/logs` | GET | Get Job Logs | 任务调度 |
| `/api/v1/scheduler/jobs/{job_id}/pause` | POST | Pause Job | 任务调度 |
| `/api/v1/scheduler/jobs/{job_id}/resume` | POST | Resume Job | 任务调度 |
| `/api/v1/scheduler/jobs/{job_id}/run` | POST | Run Job | 任务调度 |
| `/api/v1/sector/hot` | GET | Get Hot Sectors | 问财查询 |
| `/health` | GET | Health Check | - |

## TuShare-API (http://127.0.0.1:8005)

| 接口路径 | 方法 | 摘要 | 标签 |
| :--- | :--- | :--- | :--- |
| `/api/v1/index/basic` | GET | Index Basic | Tushare数据 |
| `/api/v1/index/daily` | GET | Index Daily | Tushare数据 |
| `/api/v1/stock/adj_factor` | GET | Stock Adj Factor | Tushare数据 |
| `/api/v1/stock/basic` | GET | Stock Basic | Tushare数据 |
| `/api/v1/stock/daily` | GET | Stock Daily | Tushare数据 |
| `/api/v1/suspend_d` | GET | Suspend D | Tushare数据 |
| `/api/v1/trade_cal` | GET | Trade Cal | Tushare数据 |
| `/health` | GET | Health Check | - |

## Monitor-Service (http://127.0.0.1:8006)

| 接口路径 | 方法 | 摘要 | 标签 |
| :--- | :--- | :--- | :--- |
| `/api/v1/calculate` | POST | Calculate | - |
| `/api/v1/sync/daily` | POST | Sync Daily | - |
| `/health` | GET | Health | - |

