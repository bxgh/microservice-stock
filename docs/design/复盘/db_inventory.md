# 数据库表结构与空间占用报告

- **生成时间**: 2026-05-01 21:43:00
- **数据库名**: `alwaysup`

## 行情与原始数据 (Market Raw Data)

### 表: `daily_basic`
- **描述**: 无备注
- **行数**: 11,199,147
- **占用空间**: 1638.82 MB (数据: 1297.88MB, 索引: 340.94MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(10) | No | PRI | TS代码 |
| trade_date | date | No | PRI | 交易日期 |
| close | float | Yes | None | 当日收盘价 |
| turnover_rate | float | Yes | None | 换手率(%) |
| turnover_rate_f | float | Yes | None | 换手率(自由流通股) |
| volume_ratio | float | Yes | None | 量比 |
| pe | float | Yes | None | 市盈率(总市值/净利润, 亏损的PE为空) |
| pe_ttm | float | Yes | None | 市盈率(TTM,亏损的PE为空) |
| pb | float | Yes | None | 市净率(总市值/净资产) |
| ps | float | Yes | None | 市销率 |
| ps_ttm | float | Yes | None | 市销率(TTM) |
| dv_ratio | float | Yes | None | 股息率 (%) |
| dv_ttm | float | Yes | None | 股息率(TTM)(%) |
| total_share | float | Yes | None | 总股本 (万股) |
| float_share | float | Yes | None | 流通股本 (万股) |
| free_share | float | Yes | None | 自由流通股本 (万) |
| total_mv | float | Yes | None | 总市值 (万元) |
| circ_mv | float | Yes | None | 流通市值(万元) |

---

### 表: `daily_basic_api`
- **描述**: 收盘数据api
- **行数**: 402,741
- **占用空间**: 75.22 MB (数据: 54.64MB, 索引: 20.58MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(10) | No | PRI | 代码 |
| trade_date | date | No | PRI | 交易日期 |
| ts_name | varchar(50) | Yes | None | 股票名称 |
| title | varchar(50) | No | PRI | 数据名称 |
| value | float | No | None | 数据数值 |
| unit | char(10) | Yes | None | 数值单位 |

---

### 表: `daily_basic_mv_count`
- **描述**: 无备注
- **行数**: 8,335
- **占用空间**: 1.52 MB (数据: 1.52MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | Yes | None |  |
| total_stocks | bigint(20) | Yes | None |  |
| mv_5y | double | Yes | None |  |
| mv_5y_30y | double | Yes | None |  |
| mv_30y_1by | double | Yes | None |  |
| mv_1by_5by | double | Yes | None |  |
| mv_5by_1ky | double | Yes | None |  |
| mv_1ky_5ky | double | Yes | None |  |
| mv_5ky_1wy | double | Yes | None |  |
| mv_1wy_2wy | double | Yes | None |  |
| mv_above2wy | tinyint(1) | Yes | None |  |
| mvTop100Sum | double | Yes | None |  |
| mvTop100SumPercent | double | Yes | None |  |

---

### 表: `daily_info`
- **描述**: 无备注
- **行数**: 125,666
- **占用空间**: 12.55 MB (数据: 12.55MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI | TS代码 |
| trade_date | date | No | PRI | 交易日期 |
| ts_name | varchar(50) | No | None | 市场名称 |
| com_count | int(11) | No | None | 挂牌数 |
| total_share | float | No | None | 总股本（亿股） |
| float_share | float | No | None | 流通股本（亿股） |
| total_mv | float | No | None | 总市值（亿元） |
| float_mv | float | No | None | 流通市值（亿元） |
| amount | float | No | None | 交易金额（亿元） |
| vol | float | No | None | 成交量（亿股） |
| trans_count | int(11) | No | None | 成交笔数（万笔） |
| pe | float | Yes | None | 平均市盈率 |
| tr | float | Yes | None | 换手率（％），注：深交所暂无此列 |
| exchange | varchar(50) | No | None | 交易所（SH上交所 SZ深交所） |

---

### 表: `daily_turnover_statistics`
- **描述**: 无备注
- **行数**: 8,385
- **占用空间**: 1.52 MB (数据: 1.52MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | Yes | None |  |
| trade_date | date | Yes | None |  |
| turnover_1pct | int(11) | Yes | None |  |
| turnover_1_5pct | int(11) | Yes | None |  |
| turnover_5_10pct | int(11) | Yes | None |  |
| turnover_above_10pct | int(11) | Yes | None |  |
| turnoverAbove5PctRatio | double | Yes | None | 换手率大于5%占股票总数百分比 |
| turnoverAbove5_mvChg | double | Yes | None | 换手率5%以上个股流通市值涨跌(亿元) |

---

### 表: `market_margin_summary`
- **描述**: 无备注
- **行数**: 588
- **占用空间**: 0.06 MB (数据: 0.06MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| margin_buy | decimal(20,2) | Yes | None | 两市合计融资买入额 |
| margin_balance | decimal(20,2) | Yes | None | 两市合计融资余额 |
| updated_at | timestamp | No | None |  |

---

### 表: `raw_capital_flow_summary`
- **描述**: 无备注
- **行数**: 2,649
- **占用空间**: 0.13 MB (数据: 0.13MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| north_net_inflow | decimal(20,2) | Yes | None | 北向资金当日净流入(元) |
| updated_at | timestamp | No | None |  |

---

### 表: `raw_market_stats`
- **描述**: 无备注
- **行数**: 0
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| advance_count | int(11) | Yes | None | 上涨家数 |
| decline_count | int(11) | Yes | None | 下跌家数 |
| total_market_cap | decimal(20,2) | Yes | None | 全市场总市值 |
| avg_turnover | decimal(10,4) | Yes | None | 平均换手率 |
| updated_at | timestamp | No | None |  |

---

### 表: `raw_sector_daily`
- **描述**: 无备注
- **行数**: 141,851
- **占用空间**: 20.55 MB (数据: 13.52MB, 索引: 7.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 行业代码或ETF代码 |
| trade_date | date | No | MUL |  |
| open | decimal(16,4) | Yes | None |  |
| high | decimal(16,4) | Yes | None |  |
| low | decimal(16,4) | Yes | None |  |
| close | decimal(16,4) | Yes | None |  |
| volume | decimal(20,2) | Yes | None |  |
| amount | decimal(20,2) | Yes | None |  |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_block_trade`
- **描述**: 大宗交易表
- **行数**: 298,162
- **占用空间**: 69.60 MB (数据: 54.08MB, 索引: 15.52MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| trade_date | date | No | MUL | 交易日期 |
| price | decimal(10,4) | Yes | None | 成交价 |
| volume | bigint(20) | Yes | None | 成交量 |
| amount | decimal(20,2) | Yes | None | 成交额 |
| buyer | varchar(255) | Yes | None | 买方营业部 |
| seller | varchar(255) | Yes | None | 卖方营业部 |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_lhb_daily`
- **描述**: 龙虎榜每日明细表
- **行数**: 6,643
- **占用空间**: 2.08 MB (数据: 1.52MB, 索引: 0.56MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| trade_date | date | No | MUL | 交易日期 |
| close_price | decimal(10,4) | Yes | None | 收盘价 |
| change_pct | decimal(10,4) | Yes | None | 涨跌幅 |
| turnover_rate | decimal(10,4) | Yes | None | 换手率 |
| net_buy_amt | decimal(20,2) | Yes | None | 龙虎榜净买入额 |
| buy_amt | decimal(20,2) | Yes | None | 龙虎榜买入额 |
| sell_amt | decimal(20,2) | Yes | None | 龙虎榜卖出额 |
| turnover_amt | decimal(20,2) | Yes | None | 龙虎榜成交额 |
| reason | text | Yes | None | 上榜原因 |
| inst_net_buy_amt | decimal(20,2) | Yes | None | 机构净买入额 |
| inst_buy_amt | decimal(20,2) | Yes | None | 机构买入额 |
| inst_sell_amt | decimal(20,2) | Yes | None | 机构卖出额 |
| inst_buy_count | int(11) | Yes | None | 买入机构数 |
| inst_sell_count | int(11) | Yes | None | 卖出机构数 |
| updated_at | timestamp | No | None |  |

---

## 财务与基本面 (Financial Data)

### 表: `stock_balance_sheet`
- **描述**: 资产负债表
- **行数**: 274,838
- **占用空间**: 52.10 MB (数据: 42.58MB, 索引: 9.52MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 600519.SH |
| report_date | date | No | None | 报告期日期 (如 2023-12-31) |
| notice_date | date | Yes | None | 公告日期 |
| total_assets | decimal(20,4) | Yes | None | 资产总计 |
| total_liabilities | decimal(20,4) | Yes | None | 负债合计 |
| total_equity | decimal(20,4) | Yes | None | 所有者权益合计 |
| total_equity_ato_parent | decimal(20,4) | Yes | None | 归属于母公司股东权益合计 |
| monetary_funds | decimal(20,4) | Yes | None | 货币资金 |
| accounts_receivable | decimal(20,4) | Yes | None | 应收账款 |
| notes_receivable | decimal(20,4) | Yes | None | 应收票据 |
| inventory | decimal(20,4) | Yes | None | 存货 |
| goodwill | decimal(20,4) | Yes | None | 商誉 |
| short_term_borrowings | decimal(20,4) | Yes | None | 短期借款 |
| long_term_borrowings | decimal(20,4) | Yes | None | 长期借款 |
| total_non_current_assets | decimal(20,4) | Yes | None | 非流动资产合计 |
| total_current_assets | decimal(20,4) | Yes | None | 流动资产合计 |
| total_non_current_liabilities | decimal(20,4) | Yes | None | 非流动负债合计 |
| total_current_liabilities | decimal(20,4) | Yes | None | 流动负债合计 |
| created_at | timestamp | No | None |  |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_cash_flow_statement`
- **描述**: 现金流量表
- **行数**: 277,039
- **占用空间**: 39.08 MB (数据: 29.56MB, 索引: 9.52MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| ts_code | varchar(20) | No | MUL |  |
| report_date | date | No | None |  |
| notice_date | date | Yes | None |  |
| net_operating_cash_flow | decimal(20,4) | Yes | None | 经营活动产生的现金流量净额 |
| net_investing_cash_flow | decimal(20,4) | Yes | None | 投资活动产生的现金流量净额 |
| net_financing_cash_flow | decimal(20,4) | Yes | None | 筹资活动产生的现金流量净额 |
| capex | decimal(20,4) | Yes | None | 购建固定资产、无形资产和其他长期资产支付的现金 |
| free_cash_flow | decimal(20,4) | Yes | None | 自由现金流 (计算得 OCF-CAPEX) |
| cash_and_equivalents_at_end | decimal(20,4) | Yes | None | 期末现金及现金等价物余额 |
| created_at | timestamp | No | None |  |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_finance_indicators`
- **描述**: 个股财务衍生指标表
- **行数**: 330,997
- **占用空间**: 52.13 MB (数据: 39.58MB, 索引: 12.55MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 (如 600519.SH) |
| report_date | date | No | None | 报告期日期 |
| roe | decimal(20,4) | Yes | None | 净资产收益率 (%) |
| roa | decimal(20,4) | Yes | None | 总资产收益率 (%) |
| netprofit_margin | decimal(20,4) | Yes | None | 销售净利率 (%) |
| grossprofit_margin | decimal(20,4) | Yes | None | 销售毛利率 (%) |
| asset_liab_ratio | decimal(20,4) | Yes | None | 资产负债率 (%) |
| current_ratio | decimal(20,4) | Yes | None | 流动比率 |
| eps | decimal(20,4) | Yes | None | 基本每股收益 (元) |
| created_at | timestamp | No | None |  |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_income_statement`
- **描述**: 利润表
- **行数**: 291,861
- **占用空间**: 64.11 MB (数据: 54.59MB, 索引: 9.52MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| ts_code | varchar(20) | No | MUL |  |
| report_date | date | No | None |  |
| notice_date | date | Yes | None |  |
| total_revenue | decimal(20,4) | Yes | None | 营业总收入 |
| operating_revenue | decimal(20,4) | Yes | None | 营业收入 |
| total_operating_cost | decimal(20,4) | Yes | None | 营业总成本 |
| operating_cost | decimal(20,4) | Yes | None | 营业成本 |
| selling_expenses | decimal(20,4) | Yes | None | 销售费用 |
| administrative_expenses | decimal(20,4) | Yes | None | 管理费用 |
| financial_expenses | decimal(20,4) | Yes | None | 财务费用 |
| research_expenses | decimal(20,4) | Yes | None | 研发费用 |
| operating_profit | decimal(20,4) | Yes | None | 营业利润 |
| total_profit | decimal(20,4) | Yes | None | 利润总额 |
| net_profit | decimal(20,4) | Yes | None | 净利润 |
| parent_net_profit | decimal(20,4) | Yes | None | 归属于母公司所有者的净利润 |
| deducted_net_profit | decimal(20,4) | Yes | None | 扣除非经常性损益后的净利润 |
| ebit | decimal(20,4) | Yes | None | 息税前利润 (计算得) |
| ebitda | decimal(20,4) | Yes | None | 息税折旧摊销前利润 (计算得) |
| created_at | timestamp | No | None |  |
| updated_at | timestamp | No | None |  |

---

## 监控与指标层 (Monitor & Indicators)

### 表: `monitor_health_scores`
- **描述**: 无备注
- **行数**: 6,292
- **占用空间**: 0.27 MB (数据: 0.27MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| total_score | double | Yes | None |  |
| status | varchar(20) | Yes | None |  |

---

### 表: `monitor_indicators_history`
- **描述**: 无备注
- **行数**: 24,016
- **占用空间**: 5.53 MB (数据: 2.50MB, 索引: 3.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| indicator_name | varchar(50) | No | PRI |  |
| indicator_value | double | Yes | None |  |
| score | double | Yes | None |  |

---

## 系统审计与元数据 (System & Metadata)

### 表: `commands`
- **描述**: 无备注
- **行数**: 5
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| task_id | varchar(50) | No | None |  |
| params | json | Yes | None |  |
| status | varchar(20) | Yes | None |  |
| result | text | Yes | None |  |
| created_at | datetime | Yes | None |  |
| executed_at | datetime | Yes | None |  |
| finished_at | datetime | Yes | None |  |
| request_id | varchar(50) | Yes | None |  |

---

### 表: `data_audit_details`
- **描述**: 数据校验详情明细表
- **行数**: 55
- **占用空间**: 0.24 MB (数据: 0.22MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI | 自增主键 |
| summary_id | bigint(20) | No | MUL | 关联汇总ID |
| dimension | varchar(64) | No | None | 校验维度: availability, continuity, price... |
| level | varchar(16) | No | None | 问题级别: PASS, WARN, FAIL |
| message | varchar(512) | Yes | None | 具体问题描述 |
| context | json | Yes | None | 上下文数据(JSON) |
| created_at | datetime | Yes | None | 创建时间 |

---

### 表: `data_audit_summaries`
- **描述**: 数据校验结果汇总表
- **行数**: 13
- **占用空间**: 0.07 MB (数据: 0.02MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI | 自增主键 |
| data_type | varchar(32) | No | MUL | 数据类型: tick, kline, market |
| target | varchar(64) | No | None | 校验目标: 股票代码或日期(YYYY-MM-DD) |
| trade_date | date | No | MUL | 业务交易日期 |
| level | varchar(16) | No | MUL | 校验结果级别: PASS, WARN, FAIL |
| issue_count | int(11) | Yes | None | 问题总数 |
| description | varchar(255) | Yes | None | 结果简述 |
| created_at | datetime | Yes | None | 创建时间 |
| updated_at | datetime | Yes | None | 更新时间 |

---

### 表: `data_gate_audits`
- **描述**: 精简版数据门禁每日审计历史
- **行数**: 55
- **占用空间**: 0.04 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| trade_date | date | No | MUL | 交易日期 |
| gate_id | varchar(20) | No | None | GATE_1/2/3 |
| is_complete | tinyint(1) | No | None | 1: 完整, 0: 不完整 |
| description | varchar(255) | Yes | None | 简要结果说明 |
| created_at | datetime | Yes | None |  |

---

## 其他与备份 (Others/Legacy)

### 表: `anal_result`
- **描述**: 无备注
- **行数**: 21,280
- **占用空间**: 96.56 MB (数据: 96.56MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| anal_type | int(11) | No | PRI |  |
| anal_name | varchar(100) | Yes | None |  |
| ts_code_list | text | Yes | None |  |
| stock_count | int(11) | Yes | None |  |

---

### 表: `CCI_alerts`
- **描述**: 无备注
- **行数**: 0
- **占用空间**: 0.05 MB (数据: 0.02MB, 索引: 0.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL |  |
| alert_date | datetime | No | MUL |  |
| layer | varchar(10) | No | None |  |
| alert_type | varchar(20) | No | None | 预警类型: CRITICAL_SLOWING, DISLOCATION |
| severity | varchar(10) | No | None |  |
| message | text | No | None |  |
| meta_data | json | Yes | None |  |
| is_read | tinyint(1) | No | None |  |
| created_at | datetime | No | None |  |

---

### 表: `CCI_dislocations`
- **描述**: 无备注
- **行数**: 0
- **占用空间**: 0.04 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| trade_date | datetime | No | MUL |  |
| base_layer | varchar(10) | No | None | 基准层级 |
| target_layer | varchar(10) | No | None | 对比层级 |
| dislocation_score | float | No | None | 错位分值 |
| direction | int(11) | No | None | 方向: 1(向上错位), -1(向下错位) |
| created_at | datetime | No | None |  |

---

### 表: `CCI_records`
- **描述**: 无备注
- **行数**: 0
- **占用空间**: 0.08 MB (数据: 0.02MB, 索引: 0.06MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票/指数代码 |
| trade_date | datetime | No | MUL | 交易日期 |
| cci_value | float | No | None | CCI 计算值 |
| rho_value | float | No | None | 横截面相关性 Rho |
| var_value | float | No | None | 方差 Var |
| layer | varchar(10) | No | MUL | 监测层级 L1-L6 |
| is_critical | tinyint(1) | No | None | 是否处于临界状态 |
| created_at | datetime | No | None |  |

---

### 表: `data_quality_reports`
- **描述**: 无备注
- **行数**: 1
- **占用空间**: 0.05 MB (数据: 0.02MB, 索引: 0.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| report_type | varchar(20) | No | MUL |  |
| overall_status | varchar(20) | No | None |  |
| check_time | datetime | No | MUL |  |
| report_content | json | No | None |  |
| created_at | timestamp | No | None |  |

---

---

## 股市日记与盘后复盘 (Diary & Market Review)

### 表: `fupan_data`
- **描述**: 复盘数据表
- **行数**: 0
- **占用空间**: 0.04 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI | 主键ID |
| date | date | No | UNI | 复盘日期（唯一） |
| comprehensive_description | text | Yes | None | 大盘整体走势描述（如趋势、情绪、量能等） |
| index_change | text | Yes | None | 主要指数涨跌幅及走势分析（如上证、深成指、创业板等） |
| top_concept_changes | text | Yes | None | 当日热门概念板块变化及涨幅情况总述 |
| concept_1_name | varchar(100) | Yes | None | 第一热门概念板块名称 |
| concept_1_change | varchar(20) | Yes | None | 第一热门概念板块涨跌幅（如 +5.2%） |
| concept_2_name | varchar(100) | Yes | None | 第二热门概念板块名称 |
| concept_2_change | varchar(20) | Yes | None | 第二热门概念板块涨跌幅（如 +4.8%） |
| concept_3_name | varchar(100) | Yes | None | 第三热门概念板块名称 |
| concept_3_change | varchar(20) | Yes | None | 第三热门概念板块涨跌幅（如 +4.1%） |
| main_highlights | text | Yes | None | 当日市场主要亮点（如龙头股、政策影响、热点事件等） |
| stock_activity | text | Yes | None | 个股活跃度分析（如涨停/跌停数量、换手率、成交量等） |
| sealing_efficiency | text | Yes | None | 封板效率分析（涨停封板率、炸板情况等） |
| created_at | timestamp | No | None | 记录创建时间 |

---

### 表: `diary_entry`
- **描述**: 日记主表
- **行数**: 19
- **占用空间**: 0.11 MB (数据: 0.02MB, 索引: 0.09MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| user_id | bigint(20) unsigned | No | MUL | 所属用户 |
| slug | varchar(32) | Yes | UNI | 分享 URL 短串,私密日记 NULL |
| entry_date | date | No |  | 归属交易日,与 created_at 区分 |
| entry_type | tinyint(4) | No |  | 1=盘前 2=盘中 3=盘后 4=周复盘 5=随笔 6=个股研究 |
| mood | tinyint(4) | Yes |  | 情绪 1=冷静 2=兴奋 3=焦虑 4=恐惧 5=贪婪 6=困惑,NULL=未标 |
| title | varchar(128) | Yes | MUL | 标题,可空 |
| content | mediumtext | No |  | Markdown 正文 |
| content_format | varchar(16) | No |  | 正文格式版本 |
| excerpt | varchar(255) | Yes |  | 摘要,前 60 字纯文本 |
| word_count | int(10) unsigned | No |  | 字数 |
| cover_attachment_id | bigint(20) unsigned | Yes |  | 封面图,引用 diary_attachment.id |
| visibility | tinyint(4) | No |  | 0=私密 1=链接可见 2=公开 |
| is_pinned | tinyint(1) | No |  | 是否置顶 |
| mp_published_count | int(10) unsigned | No |  | 发布到公众号次数 |
| last_exported_at | datetime | Yes |  | 最近一次成功导出时间 |
| meta | json | Yes |  |  |
| created_at | datetime | No |  |  |
| updated_at | datetime | No |  |  |
| deleted_at | datetime | Yes |  |  |

---

### 表: `diary_stock`
- **描述**: 日记股票关联
- **行数**: 10
- **占用空间**: 0.06 MB (数据: 0.02MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| diary_id | bigint(20) unsigned | No | MUL |  |
| stock_id | bigint(20) unsigned | No | MUL |  |
| ts_code | varchar(16) | No | MUL | 冗余,便于免 JOIN 查询 |
| position_in_content | int(10) unsigned | Yes |  | 在正文中首次出现的位置,可用于排序 |
| created_at | datetime | No |  |  |

---

### 表: `diary_tag`
- **描述**: 日记标签关联
- **行数**: 9
- **占用空间**: 0.05 MB (数据: 0.02MB, 索引: 0.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| diary_id | bigint(20) unsigned | No | MUL |  |
| tag_id | bigint(20) unsigned | No | MUL |  |
| created_at | datetime | No |  |  |

---

### 表: `diary_tag_dict`
- **描述**: 标签字典
- **行数**: 24
- **占用空间**: 0.05 MB (数据: 0.02MB, 索引: 0.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| owner_user_id | bigint(20) unsigned | Yes | MUL | NULL=系统标签,有值=用户自定义 |
| name | varchar(32) | No |  | 标签名,不含 # 前缀 |
| category | tinyint(4) | No |  | 0=普通 1=系统预置 2=错题本 3=策略类 |
| color | varchar(8) | Yes |  | 颜色 hex,可选 |
| usage_count | int(10) unsigned | No |  | 使用次数,定时刷新 |
| created_at | datetime | No |  |  |
| updated_at | datetime | No |  |  |
| deleted_at | datetime | Yes |  |  |

---

### 表: `diary_attachment`
- **描述**: 日记附件
- **行数**: 0
- **占用空间**: 0.06 MB (数据: 0.02MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| user_id | bigint(20) unsigned | No | MUL | 冗余,便于按用户统计配额 |
| diary_id | bigint(20) unsigned | Yes | MUL | 关联日记,NULL=已上传未关联 |
| cos_key | varchar(255) | No | UNI | COS 对象 key,如 diary/uid/202604/abc.jpg |
| mime_type | varchar(64) | No |  |  |
| size_bytes | int(10) unsigned | No |  |  |
| width | int(10) unsigned | Yes |  | 图片宽度 px |
| height | int(10) unsigned | Yes |  | 图片高度 px |
| original_name | varchar(128) | Yes |  | 原始文件名 |
| wx_media_id | varchar(128) | Yes |  | 微信永久素材 ID |
| wx_media_url | varchar(512) | Yes |  | 微信素材 URL |
| wx_uploaded_at | datetime | Yes |  |  |
| created_at | datetime | No |  |  |
| updated_at | datetime | No |  |  |
| deleted_at | datetime | Yes |  |  |

---

### 表: `diary_export_task`
- **描述**: 日记导出任务
- **行数**: 0
- **占用空间**: 0.05 MB (数据: 0.02MB, 索引: 0.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| user_id | bigint(20) unsigned | No | MUL |  |
| task_type | tinyint(4) | No |  | 1=单篇 2=按月 3=按年 4=全量 5=自定义 |
| format | varchar(16) | No |  | md(V1 仅支持)/pdf/zip |
| scope | json | No |  | 导出范围参数 |
| status | tinyint(4) | No | MUL | 0=排队 1=处理中 2=成功 3=失败 4=已过期 |
| progress | tinyint(4) | No |  | 0-100 |
| entry_count | int(10) unsigned | No |  | 导出日记数 |
| output_cos_key | varchar(255) | Yes |  |  |
| output_size_bytes | int(10) unsigned | Yes |  |  |
| download_url | varchar(512) | Yes |  | 签名下载 URL,有时效 |
| expired_at | datetime | Yes |  | 下载链接过期时间,默认 7 天 |
| downloaded_count | int(10) unsigned | No |  |  |
| error_code | varchar(32) | Yes |  |  |
| error_message | varchar(512) | Yes |  |  |
| retry_count | tinyint(3) unsigned | No |  |  |
| created_at | datetime | No |  |  |
| started_at | datetime | Yes |  |  |
| finished_at | datetime | Yes |  |  |
| updated_at | datetime | No |  |  |

---

### 表: `kday_daily_all`
- **描述**: 无备注
- **行数**: 12,915,540
- **占用空间**: 1743.97 MB (数据: 1326.00MB, 索引: 417.97MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(10) | No | PRI |  |
| trade_date | date | No | PRI |  |
| open | float | Yes | None |  |
| high | float | Yes | None |  |
| low | float | Yes | None |  |
| close | float | Yes | None |  |
| pre_close | float | Yes | None |  |
| change | float | Yes | None |  |
| pct_chg | float | Yes | None |  |
| vol | float | Yes | None |  |
| amount | float | Yes | None |  |

---

### 表: `market_amount`
- **描述**: 无备注
- **行数**: 7,561
- **占用空间**: 0.88 MB (数据: 0.50MB, 索引: 0.38MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(50) | No | PRI |  |
| trade_date | date | No | PRI |  |
| amount | decimal(8,0) | Yes | None |  |
| amount_chg | decimal(8,0) | Yes | None |  |
| float_mv | decimal(8,0) | Yes | None |  |
| float_mv_chg | decimal(8,0) | Yes | None |  |
| ma5 | decimal(8,0) | Yes | None |  |
| ma10 | decimal(8,0) | Yes | None |  |
| ma20 | decimal(8,0) | Yes | None |  |

---

### 表: `market_review_liquidity`
- **描述**: 全市场微观与宏观流动性二阶趋势表
- **行数**: 302
- **占用空间**: 0.05 MB (数据: 0.05MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI | 交易日期 |
| vol_ma_divergence | decimal(10,4) | Yes | None | VOL-01 成交额均线背离(动能差) |
| vol_rank | decimal(6,4) | Yes | None |  |
| vol_ma5_rank | decimal(6,4) | Yes | None |  |
| vol_ma20_rank | decimal(6,4) | Yes | None |  |
| vol_01_state | varchar(20) | Yes | None |  |
| margin_velocity | decimal(10,4) | Yes | None | VOL-02 融资买入动量的占比加速度 |
| margin_ratio | decimal(10,4) | Yes | None |  |
| vol_02_state | varchar(20) | Yes | None |  |
| congestion_velocity | decimal(10,4) | Yes | None | VOL-03 极值拥挤度的加速度(前10%虹吸比) |
| zombie_stock_derivation | decimal(10,4) | Yes | None | VOL-04 极寒无流动性股衍生率(Z-Score) |
| cost_pulse_fdr007 | decimal(10,4) | Yes | None | VOL-05 资金成本的异常脉冲(FR007) |
| non_bank_premium | decimal(10,4) | Yes | None | VOL-05 辅助非银流动性溢价(R007-FR007) |
| etf_depletion_rate | decimal(10,4) | Yes | None | VOL-06 ETF被动护盘的效用消耗斜率 |
| updated_at | timestamp | No | None |  |

---

### 表: `migrations_history`
- **描述**: 无备注
- **行数**: 2
- **占用空间**: 0.04 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| migration_name | varchar(255) | No | UNI |  |
| applied_at | datetime | Yes | None |  |

---

### 表: `mootdx_symbol`
- **描述**: 无备注
- **行数**: 25,795
- **占用空间**: 2.52 MB (数据: 2.52MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| code | char(6) | No | PRI | 股票代码 |
| name | char(50) | No | None | 股票名称 |
| pre_close | decimal(8,2) | Yes | None | 昨日收盘 |

---

### 表: `stock_adjust_factor`
- **描述**: 股票复权因子表
- **行数**: 57,810
- **占用空间**: 14.61 MB (数据: 4.52MB, 索引: 10.09MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(16) | No | MUL | 股票代码 |
| adjust_date | date | No | MUL | 除权除息日期 |
| fore_adjust_factor | decimal(16,6) | Yes | None | 前复权因子 |
| back_adjust_factor | decimal(16,6) | Yes | None | 后复权因子 |
| adjust_factor | decimal(16,6) | Yes | None | 复权因子 |
| created_at | timestamp | No | None | 入库时间 |

---

### 表: `stock_analyst_rank`
- **描述**: 机构评级记录表
- **行数**: 238
- **占用空间**: 0.04 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 标准代码 600519.SH |
| report_date | date | No | None |  |
| analyst | varchar(50) | No | None | 机构/分析师名称 |
| rating | varchar(20) | No | None | 评级 (买入/增持/中性) |
| change_direction | varchar(10) | Yes | None | 变动 (维持/调高/调低) |
| target_price | decimal(10,2) | Yes | None | 目标价 |
| created_at | timestamp | No | None |  |

---

### 表: `stock_basic_info`
- **描述**: 无备注
- **行数**: 5,933
- **占用空间**: 1.52 MB (数据: 1.52MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI | TS代码 |
| symbol | varchar(10) | Yes | None | 股票代码 |
| name | varchar(100) | Yes | None | 股票名称 |
| area | varchar(50) | Yes | None | 地域 |
| industry | varchar(50) | Yes | None | 所属行业 |
| fullname | varchar(200) | Yes | None | 股票全称 |
| enname | varchar(200) | Yes | None | 英文全称 |
| cnspell | varchar(20) | Yes | None | 拼音缩写 |
| market | varchar(20) | Yes | None | 市场类型（主板/创业板/科创板/CDR） |
| exchange | varchar(20) | Yes | None | 交易所代码 |
| curr_type | varchar(10) | Yes | None | 交易货币 |
| list_status | varchar(10) | Yes | None | 上市状态 L上市 D退市 P暂停上市 |
| list_date | date | Yes | None | 上市日期 |
| delist_date | date | Yes | None | 退市日期 |
| is_hs | varchar(1) | Yes | None | 是否沪深港通标的，N否 H沪股通 S深股通 |
| act_name | varchar(100) | Yes | None | 实控人名称 |
| act_ent_type | varchar(50) | Yes | None | 实控人企业性质 |
| issue_price | decimal(10,2) | Yes | None | 发行价格 |
| finance_sync_time | datetime | Yes | None | 最后一次成功同步全量财务数据的时间 |

---

### 表: `stock_health_ledger`
- **描述**: 无备注
- **行数**: 100
- **占用空间**: 0.05 MB (数据: 0.02MB, 索引: 0.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI |  |
| status | varchar(10) | No | MUL |  |
| listing_date | date | Yes | None |  |
| missing_count | int(11) | Yes | None |  |
| missing_details | json | Yes | None |  |
| suspension_count | int(11) | Yes | None |  |
| last_scan_time | datetime | Yes | MUL |  |
| repair_status | int(11) | Yes | None |  |
| created_at | timestamp | No | None |  |

---

### 表: `stock_industry_em`
- **描述**: 东方财富行业分类表
- **行数**: 0
- **占用空间**: 0.07 MB (数据: 0.02MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 (如 600519.SH) |
| industry_code | varchar(20) | No | MUL | 东方财富行业代码 (如 BK0473) |
| industry_name | varchar(50) | No | None | 东方财富行业名称 (如 半导体) |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_industry_sw`
- **描述**: 申万行业分类明细
- **行数**: 4,645
- **占用空间**: 2.19 MB (数据: 1.52MB, 索引: 0.67MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI | 标准股票代码 |
| l1_code | varchar(20) | Yes | MUL | 一级行业代码 |
| l1_name | varchar(50) | Yes | None | 一级行业名称 |
| l2_code | varchar(20) | Yes | MUL | 二级行业代码 |
| l2_name | varchar(50) | Yes | None | 二级行业名称 |
| l3_code | varchar(20) | Yes | MUL | 三级行业代码 |
| l3_name | varchar(50) | Yes | None | 三级行业名称 |
| update_time | datetime | Yes | None |  |

---

### 表: `stock_industry_ths`
- **描述**: 同花顺行业分类表 (L1/L2/L3)
- **行数**: 5,579
- **占用空间**: 1.22 MB (数据: 0.45MB, 索引: 0.77MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | UNI | 股票代码 (如 600519.SH) |
| l1_name | varchar(50) | Yes | MUL | 同花顺一级行业 |
| l2_name | varchar(50) | Yes | MUL | 同花顺二级行业 |
| l3_name | varchar(50) | Yes | MUL | 同花顺三级行业 |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_kline_daily`
- **描述**: 无备注
- **行数**: 18,308,435
- **占用空间**: 4220.48 MB (数据: 2356.50MB, 索引: 1863.98MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| ts_code | varchar(16) | No | MUL |  |
| trade_date | date | No | MUL |  |
| open | decimal(16,4) | Yes | None |  |
| high | decimal(16,4) | Yes | None |  |
| low | decimal(16,4) | Yes | None |  |
| close | decimal(16,4) | Yes | None |  |
| pre_close | decimal(16,4) | Yes | None |  |
| volume | bigint(20) | Yes | None |  |
| amount | decimal(20,4) | Yes | None |  |
| turnover | decimal(16,6) | Yes | None |  |
| pct_chg | decimal(16,6) | Yes | None |  |
| trade_status | tinyint(4) | Yes | None |  |
| created_at | timestamp | No | MUL |  |

---

### 表: `stock_north_funds_daily`
- **描述**: 北向资金每日持股表
- **行数**: 1,124
- **占用空间**: 0.19 MB (数据: 0.08MB, 索引: 0.11MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| trade_date | date | No | MUL | 交易日期 |
| hold_count | bigint(20) | Yes | None | 持股数量 |
| hold_market_cap | decimal(20,2) | Yes | None | 持股市值 |
| hold_ratio | decimal(10,4) | Yes | None | 持股占比(%) |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_performance_forecast`
- **描述**: 业绩预告表
- **行数**: 29,172
- **占用空间**: 7.04 MB (数据: 5.52MB, 索引: 1.52MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| report_period | date | No | None | 报告期 |
| notice_date | date | No | None | 公告日期 |
| type | varchar(255) | Yes | None | 业绩变动类型 |
| growth_range | varchar(255) | Yes | None | 预告幅度 |
| created_at | timestamp | No | None |  |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_restricted_release`
- **描述**: 限售股解禁表
- **行数**: 43,110
- **占用空间**: 9.07 MB (数据: 4.52MB, 索引: 4.55MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| release_date | date | No | MUL | 解禁日期 |
| release_count | bigint(20) | Yes | None | 解禁数量 |
| release_market_cap | decimal(20,2) | Yes | None | 解禁市值 |
| ratio | decimal(10,4) | Yes | None | 占总股本比例 |
| holder_type | varchar(255) | Yes | None | 解禁股本类型 |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_sector_cons_ths`
- **描述**: 同花顺板块成分映射
- **行数**: 69,810
- **占用空间**: 12.07 MB (数据: 3.52MB, 索引: 8.55MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| sector_id | int(11) | No | MUL | 板块ID |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_sector_ths`
- **描述**: 同花顺板块字典
- **行数**: 736
- **占用空间**: 0.11 MB (数据: 0.06MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| sector_name | varchar(50) | No | MUL | 板块名称 |
| sector_type | enum('industry','concept') | No | None | 板块类型 |
| sector_level | varchar(10) | Yes | None | 级别 (仅限行业: L1/L2/L3) |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_sentiment_daily`
- **描述**: 每日市场热度统计
- **行数**: 0
- **占用空间**: 0.04 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL |  |
| trade_date | date | No | None |  |
| post_count | int(11) | Yes | None | 当日发帖数 |
| read_count | int(11) | Yes | None | 当日阅读数 |
| comment_count | int(11) | Yes | None | 当日评论数 |
| rank_score | int(11) | Yes | None | 股吧热度排名(如有) |

---

### 表: `stock_shareholder_count`
- **描述**: 股东户数历史表
- **行数**: 488,315
- **占用空间**: 75.15 MB (数据: 31.56MB, 索引: 43.59MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| end_date | date | No | MUL | 截止日期 |
| holder_count | int(11) | Yes | None | 股东户数 |
| holder_change_pct | decimal(24,6) | Yes | None | 户数变动比例 |
| avg_market_cap | decimal(20,2) | Yes | None | 户均持股市值 |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_suspensions`
- **描述**: 股票每日停牌记录
- **行数**: 3,725
- **占用空间**: 0.58 MB (数据: 0.22MB, 索引: 0.36MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| trade_date | date | No | MUL | 停牌日期 |
| is_suspended | tinyint(1) | Yes | None | 是否停牌 1=是 |
| reason | varchar(255) | Yes | None | 停牌原因(如有) |
| created_at | timestamp | No | None |  |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_top10_shareholders`
- **描述**: 前十大股东表
- **行数**: 2,486,968
- **占用空间**: 721.08 MB (数据: 308.78MB, 索引: 412.30MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| end_date | date | No | None | 截止日期 |
| rank | int(11) | No | None | 排名 |
| holder_name | varchar(255) | Yes | MUL | 股东名称 |
| share_type | varchar(50) | Yes | None | 股份类型 |
| hold_count | bigint(20) | Yes | None | 持股数量 |
| hold_pct | decimal(10,4) | Yes | None | 持股比例 |
| change_stat | varchar(50) | Yes | None | 变动状态 |
| updated_at | timestamp | No | None |  |

---

### 表: `stock_xr_schedules`
- **描述**: 除权除息日程表
- **行数**: 0
- **占用空间**: 0.04 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| ex_date | date | No | None | 除权除息日 |
| bonus_ratio | decimal(10,4) | Yes | None | 送转比例 |
| cash_div | decimal(10,4) | Yes | None | 每股派现 |
| created_at | timestamp | No | None |  |

---

### 表: `sync_execution_logs`
- **描述**: 本地任务执行日志表
- **行数**: 453
- **占用空间**: 0.11 MB (数据: 0.09MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| task_name | varchar(50) | No | MUL | 任务名称 |
| execution_time | datetime | No | None | 执行时间 |
| status | varchar(20) | No | None | 状态: SUCCESS, FAILED, RUNNING |
| records_processed | int(11) | Yes | None | 同步/处理记录数 |
| details | text | Yes | None | 详细日志信息 |
| duration_seconds | float | Yes | None | 耗时(秒) |

---

### 表: `sync_progress`
- **描述**: 无备注
- **行数**: 1
- **占用空间**: 0.04 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| task_name | varchar(64) | Yes | UNI |  |
| current_code | varchar(16) | Yes | None |  |
| last_index | int(11) | Yes | None |  |
| total_count | int(11) | Yes | None |  |
| status | varchar(20) | Yes | None |  |
| updated_at | timestamp | No | None |  |

---

### 表: `task_commands`
- **描述**: 异步任务命令队列
- **行数**: 531
- **占用空间**: 14.58 MB (数据: 14.52MB, 索引: 0.06MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| run_id | char(36) | Yes | MUL |  |
| step_id | varchar(100) | Yes | None |  |
| task_id | varchar(100) | No | None | 任务ID，如 pre_market_gate |
| params | json | Yes | None | 可选参数，如 {"target_date": "20260113"} |
| input_context | json | Yes | None |  |
| status | enum('PENDING','RUNNING','DONE','FAILED') | Yes | MUL |  |
| created_at | datetime | Yes | None |  |
| executed_at | datetime | Yes | None |  |
| result | text | Yes | None | 执行结果或错误信息 |
| output_context | json | Yes | None |  |

---

### 表: `task_execution_logs`
- **描述**: 任务执行日志
- **行数**: 110
- **占用空间**: 0.36 MB (数据: 0.31MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| task_id | varchar(100) | No | MUL | 任务ID |
| task_name | varchar(200) | No | None | 任务名称 |
| status | enum('RUNNING','SUCCESS','FAILED','TIMEOUT','CANCELLED') | No | MUL | 执行状态 |
| start_time | datetime | No | MUL | 开始时间 |
| end_time | datetime | Yes | None | 结束时间 |
| duration_seconds | int(11) | Yes | None | 执行耗时(秒) |
| exit_code | int(11) | Yes | None | 退出码 (0=成功) |
| error_message | text | Yes | None | 错误信息 |
| container_id | varchar(100) | Yes | None | Docker容器ID |
| metadata | json | Yes | None | 元数据 |
| created_at | datetime | Yes | None | 记录创建时间 |
| updated_at | datetime | Yes | None | 记录更新时间 |

---

### 表: `task_execution_stats`
- **描述**: VIEW
- **行数**: 0
- **占用空间**: 0.00 MB (数据: 0MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| task_id | varchar(100) | No | None | 任务ID |
| task_name | varchar(200) | No | None | 任务名称 |
| total_executions | bigint(21) | No | None |  |
| successful | decimal(23,0) | Yes | None |  |
| failed | decimal(23,0) | Yes | None |  |
| success_rate | decimal(29,2) | Yes | None |  |
| avg_duration_seconds | decimal(14,4) | Yes | None |  |
| last_run_time | datetime | Yes | None | 开始时间 |

---

### 表: `trade_cal`
- **描述**: 无备注
- **行数**: 12,720
- **占用空间**: 0.47 MB (数据: 0.47MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| cal_date | date | No | PRI | 日历日期 |
| exchange | varchar(50) | No | None | 交易所名称 (SSE 上交所, SZSE 深交所) |
| is_open | int(11) | No | None | 是否交易的标志 (0 休市, 1 交易) |
| pretrade_date | date | Yes | None | 上一个交易日的日期 |

---

### 表: `trade_date_list_for_init`
- **描述**: 空表
- **行数**: 7,472
- **占用空间**: 0.25 MB (数据: 0.25MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | Yes | None |  |

---

### 表: `ts_concept_detail`
- **描述**: 无备注
- **行数**: 0
- **占用空间**: 0.05 MB (数据: 0.02MB, 索引: 0.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| concept_name | varchar(255) | No | None |  |
| ts_code | varchar(20) | No | MUL |  |
| name | varchar(255) | No | None |  |
| in_date | date | Yes | None |  |
| out_date | date | Yes | None |  |

---

### 表: `view_market_daily_review`
- **描述**: VIEW
- **行数**: 0
- **占用空间**: 0.00 MB (数据: 0MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | None | 交易日期 |
| vol_ma_divergence | decimal(10,4) | Yes | None | VOL-01 成交额均线背离(动能差) |
| vol_rank | decimal(6,4) | Yes | None |  |
| vol_ma5_rank | decimal(6,4) | Yes | None |  |
| vol_ma20_rank | decimal(6,4) | Yes | None |  |
| vol_01_state | varchar(20) | Yes | None |  |
| margin_velocity | decimal(10,4) | Yes | None | VOL-02 融资买入动量的占比加速度 |
| congestion_velocity | decimal(10,4) | Yes | None | VOL-03 极值拥挤度的加速度(前10%虹吸比) |
| zombie_stock_derivation | decimal(10,4) | Yes | None | VOL-04 极寒无流动性股衍生率(Z-Score) |
| cost_pulse_fdr007 | decimal(10,4) | Yes | None | VOL-05 资金成本的异常脉冲(FR007) |
| non_bank_premium | decimal(10,4) | Yes | None | VOL-05 辅助非银流动性溢价(R007-FR007) |
| etf_depletion_rate | decimal(10,4) | Yes | None | VOL-06 ETF被动护盘的效用消耗斜率 |

---

### 表: `wencai_fund_holdings`
- **描述**: 无备注
- **行数**: 24,990
- **占用空间**: 3.52 MB (数据: 3.52MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI | TS代码 |
| name | varchar(100) | Yes | None | 股票名称 |
| end_date | date | No | PRI | 截止日期 |
| hoding_counts | int(11) | Yes | None | 持股家数 |
| mkv | float | Yes | None | 持有股票市值(元) |
| holding_amount | float | Yes | None | 截止日期持有股票数量（股） |
| stk_float_ratio | float | Yes | None | 占流通股本比例 |

---

### 表: `wencai_stock_industry`
- **描述**: 无备注
- **行数**: 5,248
- **占用空间**: 1.52 MB (数据: 1.52MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI | TS代码 |
| name | varchar(100) | No | None | 指数简称 |
| level1 | varchar(100) | No | None | 一级行业 |
| level2 | varchar(100) | No | None | 二级行业 |
| level3 | varchar(100) | No | None | 三级行业 |

---

### 表: `wencai_zd_concept_industry`
- **描述**: 无备注
- **行数**: 717
- **占用空间**: 0.08 MB (数据: 0.08MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI | TS代码 |
| name | varchar(100) | No | None | 指数简称 |
| type | varchar(100) | No | None | 行业(概念)类型 |
| level | varchar(50) | Yes | None | 行业级别 |

---

### 表: `workflow_definitions`
- **描述**: Workflow definition templates
- **行数**: 6
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | varchar(100) | No | PRI |  |
| name | varchar(255) | No | None |  |
| version | int(11) | Yes | None |  |
| definition | json | No | None | The DAG definition in JSON/YAML format |
| created_at | datetime | Yes | None |  |
| updated_at | datetime | Yes | None |  |

---

### 表: `workflow_runs`
- **描述**: Workflow instance execution tracking
- **行数**: 237
- **占用空间**: 4.35 MB (数据: 4.30MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| run_id | char(36) | No | PRI |  |
| workflow_id | varchar(100) | No | MUL |  |
| status | enum('PENDING','RUNNING','COMPLETED','FAILED','CANCELLED') | Yes | None |  |
| context | json | Yes | None | Global runtime context |
| start_time | datetime | Yes | None |  |
| end_time | datetime | Yes | None |  |

---

