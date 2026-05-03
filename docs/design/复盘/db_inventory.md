# 数据库表结构与空间占用报告

- **生成时间**: 2026-05-03 11:14:42
- **数据库名**: `alwaysup`

```sh
docker run --rm \
  -v $(pwd):/app \
  -w /app \
  --env-file .env \
  akshare-api:latest \
  python3 scripts/generate_db_inventory.py
```

## 行情与原始数据 (Market Raw Data)

### 表: `daily_basic`
- **描述**: 无备注
- **行数**: 11,199,147
- **占用空间**: 1638.81 MB (数据: 1297.88MB, 索引: 340.94MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(10) | No | PRI | TS代码 |
| trade_date | date | No | PRI | 交易日期 |
| close | float | Yes |  | 当日收盘价 |
| turnover_rate | float | Yes |  | 换手率(%) |
| turnover_rate_f | float | Yes |  | 换手率(自由流通股) |
| volume_ratio | float | Yes |  | 量比 |
| pe | float | Yes |  | 市盈率(总市值/净利润, 亏损的PE为空) |
| pe_ttm | float | Yes |  | 市盈率(TTM,亏损的PE为空) |
| pb | float | Yes |  | 市净率(总市值/净资产) |
| ps | float | Yes |  | 市销率 |
| ps_ttm | float | Yes |  | 市销率(TTM) |
| dv_ratio | float | Yes |  | 股息率 (%) |
| dv_ttm | float | Yes |  | 股息率(TTM)(%) |
| total_share | float | Yes |  | 总股本 (万股) |
| float_share | float | Yes |  | 流通股本 (万股) |
| free_share | float | Yes |  | 自由流通股本 (万) |
| total_mv | float | Yes |  | 总市值 (万元) |
| circ_mv | float | Yes |  | 流通市值(万元) |

---

### 表: `daily_basic_api`
- **描述**: 收盘数据api
- **行数**: 402,741
- **占用空间**: 75.22 MB (数据: 54.64MB, 索引: 20.58MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(10) | No | PRI | 代码 |
| trade_date | date | No | PRI | 交易日期 |
| ts_name | varchar(50) | Yes |  | 股票名称 |
| title | varchar(50) | No | PRI | 数据名称 |
| value | float | No |  | 数据数值 |
| unit | char(10) | Yes |  | 数值单位 |

---

### 表: `daily_basic_mv_count`
- **描述**: 无备注
- **行数**: 8,335
- **占用空间**: 1.52 MB (数据: 1.52MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | Yes |  |  |
| total_stocks | bigint(20) | Yes |  |  |
| mv_5y | double | Yes |  |  |
| mv_5y_30y | double | Yes |  |  |
| mv_30y_1by | double | Yes |  |  |
| mv_1by_5by | double | Yes |  |  |
| mv_5by_1ky | double | Yes |  |  |
| mv_1ky_5ky | double | Yes |  |  |
| mv_5ky_1wy | double | Yes |  |  |
| mv_1wy_2wy | double | Yes |  |  |
| mv_above2wy | tinyint(1) | Yes |  |  |
| mvTop100Sum | double | Yes |  |  |
| mvTop100SumPercent | double | Yes |  |  |

---

### 表: `daily_info`
- **描述**: 无备注
- **行数**: 125,666
- **占用空间**: 12.55 MB (数据: 12.55MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI | TS代码 |
| trade_date | date | No | PRI | 交易日期 |
| ts_name | varchar(50) | No |  | 市场名称 |
| com_count | int(11) | No |  | 挂牌数 |
| total_share | float | No |  | 总股本（亿股） |
| float_share | float | No |  | 流通股本（亿股） |
| total_mv | float | No |  | 总市值（亿元） |
| float_mv | float | No |  | 流通市值（亿元） |
| amount | float | No |  | 交易金额（亿元） |
| vol | float | No |  | 成交量（亿股） |
| trans_count | int(11) | No |  | 成交笔数（万笔） |
| pe | float | Yes |  | 平均市盈率 |
| tr | float | Yes |  | 换手率（％），注：深交所暂无此列 |
| exchange | varchar(50) | No |  | 交易所（SH上交所 SZ深交所） |

---

### 表: `daily_turnover_statistics`
- **描述**: 无备注
- **行数**: 8,385
- **占用空间**: 1.52 MB (数据: 1.52MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | Yes |  |  |
| trade_date | date | Yes |  |  |
| turnover_1pct | int(11) | Yes |  |  |
| turnover_1_5pct | int(11) | Yes |  |  |
| turnover_5_10pct | int(11) | Yes |  |  |
| turnover_above_10pct | int(11) | Yes |  |  |
| turnoverAbove5PctRatio | double | Yes |  | 换手率大于5%占股票总数百分比 |
| turnoverAbove5_mvChg | double | Yes |  | 换手率5%以上个股流通市值涨跌(亿元) |

---

### 表: `market_amount`
- **描述**: 无备注
- **行数**: 7,561
- **占用空间**: 0.88 MB (数据: 0.50MB, 索引: 0.38MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(50) | No | PRI |  |
| trade_date | date | No | PRI |  |
| amount | decimal(8,0) | Yes |  |  |
| amount_chg | decimal(8,0) | Yes |  |  |
| float_mv | decimal(8,0) | Yes |  |  |
| float_mv_chg | decimal(8,0) | Yes |  |  |
| ma5 | decimal(8,0) | Yes |  |  |
| ma10 | decimal(8,0) | Yes |  |  |
| ma20 | decimal(8,0) | Yes |  |  |

---

### 表: `market_margin_summary`
- **描述**: 无备注
- **行数**: 587
- **占用空间**: 0.06 MB (数据: 0.06MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| margin_buy | decimal(20,2) | Yes |  | 两市合计融资买入额 |
| margin_balance | decimal(20,2) | Yes |  | 两市合计融资余额 |
| updated_at | timestamp | No |  |  |

---

### 表: `market_review_liquidity`
- **描述**: 全市场微观与宏观流动性二阶趋势表
- **行数**: 302
- **占用空间**: 0.05 MB (数据: 0.05MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI | 交易日期 |
| vol_ma_divergence | decimal(10,4) | Yes |  | VOL-01 成交额均线背离(动能差) |
| vol_rank | decimal(6,4) | Yes |  |  |
| vol_ma5_rank | decimal(6,4) | Yes |  |  |
| vol_ma20_rank | decimal(6,4) | Yes |  |  |
| vol_01_state | varchar(20) | Yes |  |  |
| margin_velocity | decimal(10,4) | Yes |  | VOL-02 融资买入动量的占比加速度 |
| margin_ratio | decimal(10,4) | Yes |  |  |
| vol_02_state | varchar(20) | Yes |  |  |
| congestion_velocity | decimal(10,4) | Yes |  | VOL-03 极值拥挤度的加速度(前10%虹吸比) |
| zombie_stock_derivation | decimal(10,4) | Yes |  | VOL-04 极寒无流动性股衍生率(Z-Score) |
| cost_pulse_fdr007 | decimal(10,4) | Yes |  | VOL-05 资金成本的异常脉冲(FR007) |
| non_bank_premium | decimal(10,4) | Yes |  | VOL-05 辅助非银流动性溢价(R007-FR007) |
| etf_depletion_rate | decimal(10,4) | Yes |  | VOL-06 ETF被动护盘的效用消耗斜率 |
| updated_at | timestamp | No |  |  |

---

### 表: `ods_concept_kline_daily`
- **描述**: ODS: 概念板块日线行情
- **行数**: 474
- **占用空间**: 0.06 MB (数据: 0.06MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| concept_code | varchar(30) | No | PRI | 对应 stock_sector_ths.id |
| concept_name | varchar(80) | Yes |  |  |
| open | decimal(16,4) | Yes |  |  |
| high | decimal(16,4) | Yes |  |  |
| low | decimal(16,4) | Yes |  |  |
| close | decimal(16,4) | Yes |  |  |
| pct_chg | decimal(10,6) | Yes |  |  |
| amount | decimal(20,2) | Yes |  | 成交额(元) |
| up_count | int(11) | Yes |  | 上涨家数 |
| down_count | int(11) | Yes |  | 下跌家数 |
| constituent_count | int(11) | Yes |  | 成分股总数 |
| data_source | varchar(20) | Yes |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `ods_event_limit_pool`
- **描述**: ODS:涨跌停 / 炸板 / 连板池(每日多池共表)
- **行数**: 3,307
- **占用空间**: 1.95 MB (数据: 1.52MB, 索引: 0.44MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI | 交易日 |
| ts_code | varchar(20) | No | PRI | 股票代码,带后缀如 600519.SH |
| name | varchar(50) | Yes |  | 股票名称 |
| pool_type | varchar(20) | No | PRI | 池类型:zt(涨停)/dt(跌停)/zb(炸板)/lian(连板) |
| close | decimal(12,4) | Yes |  | 收盘价 |
| pct_chg | decimal(10,6) | Yes |  | 涨跌幅(小数) |
| amount | decimal(20,2) | Yes |  | 成交额(元) |
| circ_mv | decimal(20,2) | Yes |  | 流通市值(元) |
| turnover_rate | decimal(10,6) | Yes |  | 换手率(小数) |
| first_limit_time | time | Yes |  | 首次封板时间 |
| last_limit_time | time | Yes |  | 最后封板时间 |
| board_height | int(11) | Yes |  | 连板高度,首板=1,炸板/跌停为 NULL |
| seal_money | decimal(20,2) | Yes |  | 封单金额(元) |
| seal_count | int(11) | Yes |  | 封板次数(仅涨停池) |
| open_times | int(11) | Yes |  | 炸板次数(仅炸板池) |
| industry | varchar(50) | Yes |  | 所属行业(申万一级,enrichment) |
| concept_tags | json | Yes |  | 所属概念列表 |
| data_source | varchar(20) | Yes |  | 数据源 |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `ods_index_daily`
- **描述**: ODS:指数日线行情(Tushare index_daily 同步)
- **行数**: 10,077
- **占用空间**: 2.80 MB (数据: 2.52MB, 索引: 0.28MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI | 交易日 |
| ts_code | varchar(20) | No | PRI | 指数代码 |
| open | decimal(16,4) | Yes |  | 开盘点位 |
| high | decimal(16,4) | Yes |  | 最高点位 |
| low | decimal(16,4) | Yes |  | 最低点位 |
| close | decimal(16,4) | Yes |  | 收盘点位 |
| pre_close | decimal(16,4) | Yes |  | 昨日收盘 |
| change | decimal(16,4) | Yes |  | 涨跌额 |
| pct_chg | decimal(10,6) | Yes |  | 涨跌幅(小数,0.0123 = 1.23%) |
| vol | decimal(20,2) | Yes |  | 成交量(手,Tushare 原口径) |
| amount | decimal(20,2) | Yes |  | 成交额(千元,Tushare 原口径) |
| data_source | varchar(20) | Yes |  | 数据源 |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `ods_market_breadth_daily`
- **描述**: ODS:全市场涨跌家数与广度(每日聚合)
- **行数**: 31
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI | 交易日 |
| total_count | int(11) | Yes |  | 全 A 总数(剔除 B 股) |
| up_count | int(11) | Yes |  | 上涨家数(pct_chg > 0) |
| down_count | int(11) | Yes |  | 下跌家数(pct_chg < 0) |
| flat_count | int(11) | Yes |  | 平盘家数(pct_chg = 0) |
| suspended_count | int(11) | Yes |  | 停牌家数 |
| up_5pct_count | int(11) | Yes |  | 涨幅 ≥ 5% 家数 |
| down_5pct_count | int(11) | Yes |  | 跌幅 ≥ 5% 家数 |
| up_9pct_count | int(11) | Yes |  | 涨幅 ≥ 9% 家数(接近涨停) |
| down_9pct_count | int(11) | Yes |  | 跌幅 ≥ 9% 家数(接近跌停) |
| high_60d_count | int(11) | Yes |  | 创 60 日新高家数 |
| low_60d_count | int(11) | Yes |  | 创 60 日新低家数 |
| high_250d_count | int(11) | Yes |  | 创 250 日新高家数(年线新高) |
| low_250d_count | int(11) | Yes |  | 创 250 日新低家数 |
| data_source | varchar(20) | Yes |  | 数据源 |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `ods_sw_index_daily`
- **描述**: ODS: 申万一级/二级行业指数日线
- **行数**: 537
- **占用空间**: 0.14 MB (数据: 0.12MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| ts_code | varchar(20) | No | PRI | 行业代码, 如 801010.SI |
| name | varchar(50) | Yes |  |  |
| level | varchar(10) | No | MUL | l1=一级, l2=二级 |
| open | decimal(16,4) | Yes |  |  |
| high | decimal(16,4) | Yes |  |  |
| low | decimal(16,4) | Yes |  |  |
| close | decimal(16,4) | Yes |  |  |
| pre_close | decimal(16,4) | Yes |  |  |
| pct_chg | decimal(10,6) | Yes |  | 涨跌幅(小数) |
| vol | decimal(20,2) | Yes |  | 成交量(手) |
| amount | decimal(20,2) | Yes |  | 成交额(元) |
| pe_ttm | decimal(12,4) | Yes |  | 滚动市盈率 |
| pb | decimal(12,4) | Yes |  | 市净率 |
| dv_ratio | decimal(10,6) | Yes |  | 股息率(小数) |
| data_source | varchar(20) | Yes |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `stock_kline_daily`
- **描述**: 无备注
- **行数**: 12,624,542
- **占用空间**: 1660.47 MB (数据: 1309.47MB, 索引: 351.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(16) | No | PRI |  |
| trade_date | date | No | PRI |  |
| open | decimal(16,4) | Yes |  |  |
| high | decimal(16,4) | Yes |  |  |
| low | decimal(16,4) | Yes |  |  |
| close | decimal(16,4) | Yes |  |  |
| pre_close | decimal(16,4) | Yes |  |  |
| volume | bigint(20) | Yes |  |  |
| amount | decimal(20,4) | Yes |  |  |
| turnover | decimal(16,6) | Yes |  |  |
| pct_chg | decimal(16,6) | Yes |  |  |
| trade_status | tinyint(4) | Yes |  |  |
| created_at | timestamp | No |  |  |

---

## 财务与基本面 (Financial Data)

### 表: `stock_balance_sheet`
- **描述**: 资产负债表
- **行数**: 271,747
- **占用空间**: 52.09 MB (数据: 42.58MB, 索引: 9.52MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 600519.SH |
| report_date | date | No |  | 报告期日期 (如 2023-12-31) |
| notice_date | date | Yes |  | 公告日期 |
| total_assets | decimal(20,4) | Yes |  | 资产总计 |
| total_liabilities | decimal(20,4) | Yes |  | 负债合计 |
| total_equity | decimal(20,4) | Yes |  | 所有者权益合计 |
| total_equity_ato_parent | decimal(20,4) | Yes |  | 归属于母公司股东权益合计 |
| monetary_funds | decimal(20,4) | Yes |  | 货币资金 |
| accounts_receivable | decimal(20,4) | Yes |  | 应收账款 |
| notes_receivable | decimal(20,4) | Yes |  | 应收票据 |
| inventory | decimal(20,4) | Yes |  | 存货 |
| goodwill | decimal(20,4) | Yes |  | 商誉 |
| short_term_borrowings | decimal(20,4) | Yes |  | 短期借款 |
| long_term_borrowings | decimal(20,4) | Yes |  | 长期借款 |
| total_non_current_assets | decimal(20,4) | Yes |  | 非流动资产合计 |
| total_current_assets | decimal(20,4) | Yes |  | 流动资产合计 |
| total_non_current_liabilities | decimal(20,4) | Yes |  | 非流动负债合计 |
| total_current_liabilities | decimal(20,4) | Yes |  | 流动负债合计 |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_cash_flow_statement`
- **描述**: 现金流量表
- **行数**: 273,941
- **占用空间**: 39.08 MB (数据: 29.56MB, 索引: 9.52MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| ts_code | varchar(20) | No | MUL |  |
| report_date | date | No |  |  |
| notice_date | date | Yes |  |  |
| net_operating_cash_flow | decimal(20,4) | Yes |  | 经营活动产生的现金流量净额 |
| net_investing_cash_flow | decimal(20,4) | Yes |  | 投资活动产生的现金流量净额 |
| net_financing_cash_flow | decimal(20,4) | Yes |  | 筹资活动产生的现金流量净额 |
| capex | decimal(20,4) | Yes |  | 购建固定资产、无形资产和其他长期资产支付的现金 |
| free_cash_flow | decimal(20,4) | Yes |  | 自由现金流 (计算得 OCF-CAPEX) |
| cash_and_equivalents_at_end | decimal(20,4) | Yes |  | 期末现金及现金等价物余额 |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_finance_indicators`
- **描述**: 个股财务衍生指标表
- **行数**: 330,082
- **占用空间**: 52.12 MB (数据: 39.58MB, 索引: 12.55MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 (如 600519.SH) |
| report_date | date | No |  | 报告期日期 |
| roe | decimal(20,4) | Yes |  | 净资产收益率 (%) |
| roa | decimal(20,4) | Yes |  | 总资产收益率 (%) |
| netprofit_margin | decimal(20,4) | Yes |  | 销售净利率 (%) |
| grossprofit_margin | decimal(20,4) | Yes |  | 销售毛利率 (%) |
| asset_liab_ratio | decimal(20,4) | Yes |  | 资产负债率 (%) |
| current_ratio | decimal(20,4) | Yes |  | 流动比率 |
| eps | decimal(20,4) | Yes |  | 基本每股收益 (元) |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_income_statement`
- **描述**: 利润表
- **行数**: 288,765
- **占用空间**: 64.11 MB (数据: 54.59MB, 索引: 9.52MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| ts_code | varchar(20) | No | MUL |  |
| report_date | date | No |  |  |
| notice_date | date | Yes |  |  |
| total_revenue | decimal(20,4) | Yes |  | 营业总收入 |
| operating_revenue | decimal(20,4) | Yes |  | 营业收入 |
| total_operating_cost | decimal(20,4) | Yes |  | 营业总成本 |
| operating_cost | decimal(20,4) | Yes |  | 营业成本 |
| selling_expenses | decimal(20,4) | Yes |  | 销售费用 |
| administrative_expenses | decimal(20,4) | Yes |  | 管理费用 |
| financial_expenses | decimal(20,4) | Yes |  | 财务费用 |
| research_expenses | decimal(20,4) | Yes |  | 研发费用 |
| operating_profit | decimal(20,4) | Yes |  | 营业利润 |
| total_profit | decimal(20,4) | Yes |  | 利润总额 |
| net_profit | decimal(20,4) | Yes |  | 净利润 |
| parent_net_profit | decimal(20,4) | Yes |  | 归属于母公司所有者的净利润 |
| deducted_net_profit | decimal(20,4) | Yes |  | 扣除非经常性损益后的净利润 |
| ebit | decimal(20,4) | Yes |  | 息税前利润 (计算得) |
| ebitda | decimal(20,4) | Yes |  | 息税折旧摊销前利润 (计算得) |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_shareholder_count`
- **描述**: 股东户数历史表
- **行数**: 488,315
- **占用空间**: 75.16 MB (数据: 31.56MB, 索引: 43.59MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| end_date | date | No | MUL | 截止日期 |
| holder_count | int(11) | Yes |  | 股东户数 |
| holder_change_pct | decimal(24,6) | Yes |  | 户数变动比例 |
| avg_market_cap | decimal(20,2) | Yes |  | 户均持股市值 |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_top10_shareholders`
- **描述**: 前十大股东表
- **行数**: 2,486,968
- **占用空间**: 721.08 MB (数据: 308.78MB, 索引: 412.30MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| end_date | date | No |  | 截止日期 |
| rank | int(11) | No |  | 排名 |
| holder_name | varchar(255) | Yes | MUL | 股东名称 |
| share_type | varchar(50) | Yes |  | 股份类型 |
| hold_count | bigint(20) | Yes |  | 持股数量 |
| hold_pct | decimal(10,4) | Yes |  | 持股比例 |
| change_stat | varchar(50) | Yes |  | 变动状态 |
| updated_at | timestamp | No |  |  |

---

## 监控与指标层 (Monitor & Indicators)

### 表: `ads_l1_market_overview`
- **描述**: ADS-L1:市场全景指标(每日一行)
- **行数**: 36
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI | 交易日 |
| idx_sh_close | decimal(16,4) | Yes |  | 上证综指收盘 |
| idx_sh_pct | decimal(10,6) | Yes |  | 上证综指涨跌幅(小数) |
| idx_sz_close | decimal(16,4) | Yes |  | 深证成指收盘 |
| idx_sz_pct | decimal(10,6) | Yes |  | 深证成指涨跌幅 |
| idx_cyb_close | decimal(16,4) | Yes |  | 创业板指收盘 |
| idx_cyb_pct | decimal(10,6) | Yes |  | 创业板指涨跌幅 |
| idx_kc50_close | decimal(16,4) | Yes |  | 科创 50 收盘 |
| idx_kc50_pct | decimal(10,6) | Yes |  | 科创 50 涨跌幅 |
| idx_bz50_close | decimal(16,4) | Yes |  | 北证 50 收盘 |
| idx_bz50_pct | decimal(10,6) | Yes |  | 北证 50 涨跌幅 |
| idx_hs300_close | decimal(16,4) | Yes |  | 沪深 300 收盘 |
| idx_hs300_pct | decimal(10,6) | Yes |  | 沪深 300 涨跌幅 |
| idx_zz500_close | decimal(16,4) | Yes |  | 中证 500 收盘 |
| idx_zz500_pct | decimal(10,6) | Yes |  | 中证 500 涨跌幅 |
| idx_zz1000_close | decimal(16,4) | Yes |  | 中证 1000 收盘 |
| idx_zz1000_pct | decimal(10,6) | Yes |  | 中证 1000 涨跌幅 |
| idx_zz2000_close | decimal(16,4) | Yes |  | 中证 2000 收盘 |
| idx_zz2000_pct | decimal(10,6) | Yes |  | 中证 2000 涨跌幅 |
| idx_winda_close | decimal(16,4) | Yes |  | 万得全 A 收盘 |
| idx_winda_pct | decimal(10,6) | Yes |  | 万得全 A 涨跌幅 |
| turnover_total | decimal(20,2) | Yes |  | 全市场成交额(元) |
| turnover_ma5 | decimal(20,2) | Yes |  | 成交额 5 日均值(元) |
| turnover_ma20 | decimal(20,2) | Yes |  | 成交额 20 日均值(元) |
| turnover_pct_vs_ma20 | decimal(10,6) | Yes |  | 相对 20 日均值倍数 - 1(0.1 = 高出 10%) |
| turnover_pctile_1y | decimal(10,6) | Yes |  | 近 1 年(250 交易日)分位数(0-1) |
| up_count | int(11) | Yes |  | 上涨家数 |
| down_count | int(11) | Yes |  | 下跌家数 |
| flat_count | int(11) | Yes |  | 平盘家数 |
| up_down_ratio | decimal(10,4) | Yes |  | 涨跌比 = up / down |
| limit_up_count | int(11) | Yes |  | 涨停家数(含一字) |
| limit_down_count | int(11) | Yes |  | 跌停家数 |
| blast_count | int(11) | Yes |  | 炸板家数 |
| lian_count | int(11) | Yes |  | 连板家数(高度 ≥ 2) |
| max_board_height | int(11) | Yes |  | 当日最高板高度 |
| high_60d_count | int(11) | Yes |  | 创 60 日新高家数 |
| low_60d_count | int(11) | Yes |  | 创 60 日新低家数 |
| high_250d_count | int(11) | Yes |  | 250日新高家数 |
| low_250d_count | int(11) | Yes |  | 250日新低家数 |
| market_breadth | decimal(10,6) | Yes |  | 市场宽度 = up_count / total_count |
| market_regime | varchar(20) | Yes |  | 市场风格:broad_up/broad_down/structural/low_vol |
| compute_version | varchar(20) | Yes |  | 计算版本 |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `ads_l2_concept_daily`
- **描述**: ADS: 概念 L2 结构指标
- **行数**: 78
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| concept_code | varchar(30) | No | PRI |  |
| concept_name | varchar(80) | Yes |  |  |
| pct_chg | decimal(10,6) | Yes |  |  |
| amount | decimal(20,2) | Yes |  |  |
| turnover_rate | decimal(10,6) | Yes |  |  |
| up_count | int(11) | Yes |  |  |
| down_count | int(11) | Yes |  |  |
| constituent_count | int(11) | Yes |  |  |
| compute_version | varchar(20) | Yes |  |  |
| internal_breadth | decimal(10,6) | Yes |  |  |
| limit_up_count | int(11) | Yes |  | 概念内涨停数 |
| persistence_score | decimal(10,6) | Yes |  | 持续性评分(0-1) |
| theme_label | varchar(20) | Yes |  | main_theme/one_day/etc |
| created_at | timestamp | No |  |  |

---

### 表: `ads_l2_concept_rotation`
- **描述**: 无备注
- **行数**: 496
- **占用空间**: 0.05 MB (数据: 0.05MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| ts_code | varchar(20) | Yes |  |  |
| name | varchar(100) | No | PRI |  |
| pct_chg | decimal(8,4) | Yes |  |  |
| rank_current | int(11) | Yes |  |  |
| rank_5d_change | int(11) | Yes |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `ads_l2_industry_daily`
- **描述**: ADS: 行业 L2 结构指标
- **行数**: 93
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| industry_code | varchar(20) | No | PRI |  |
| industry_name | varchar(50) | Yes |  |  |
| close | decimal(16,4) | Yes |  |  |
| pct_chg | decimal(10,6) | Yes |  |  |
| amount | decimal(20,2) | Yes |  |  |
| turnover_rate | decimal(10,6) | Yes |  |  |
| pe_ttm | decimal(12,4) | Yes |  |  |
| pb | decimal(12,4) | Yes |  |  |
| dv_ratio | decimal(10,6) | Yes |  |  |
| up_count | int(11) | Yes |  |  |
| down_count | int(11) | Yes |  |  |
| limit_up_count | int(11) | Yes |  |  |
| total_count | int(11) | Yes |  |  |
| internal_breadth | decimal(10,6) | Yes |  | 内部广度 (up/total) |
| top_stock_code | varchar(20) | Yes |  | 领涨股代码 |
| top_stock_name | varchar(50) | Yes |  |  |
| top_stock_pct | decimal(10,6) | Yes |  |  |
| rank_today | int(11) | Yes |  | 当日涨幅排名 |
| rank_5d | int(11) | Yes |  |  |
| rank_20d | int(11) | Yes |  |  |
| rank_diff_5d | int(11) | Yes |  | 5日排名变化(负数代表走强) |
| rank_diff_20d | int(11) | Yes |  |  |
| pe_pctile_5y | decimal(10,6) | Yes |  | PE 5年分位 |
| heat_label | varchar(20) | Yes |  | hot/warm/normal/cold |
| compute_version | varchar(20) | Yes |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `ads_l2_industry_rotation`
- **描述**: 无备注
- **行数**: 62
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| ts_code | varchar(20) | Yes |  |  |
| name | varchar(50) | No | PRI |  |
| pct_chg | decimal(8,4) | Yes |  |  |
| rank_current | int(11) | Yes |  |  |
| rank_5d_change | int(11) | Yes |  |  |
| leader_stock | varchar(50) | Yes |  |  |
| pe_percentile | decimal(8,4) | Yes |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `ads_l2_structural_snapshot`
- **描述**: 无备注
- **行数**: 4
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| snapshot_payload | json | Yes |  | 包含行业、概念、风格的完整JSON |
| summary_text | text | Yes |  | 预留的文字复盘点评 |
| updated_at | timestamp | No |  |  |

---

### 表: `ads_l2_style_factor`
- **描述**: ADS: 风格 L2 结构指标
- **行数**: 6
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| factor_code | varchar(30) | No | PRI |  |
| factor_name | varchar(50) | Yes |  |  |
| long_pct | decimal(10,6) | Yes |  |  |
| short_pct | decimal(10,6) | Yes |  |  |
| spread_today | decimal(10,6) | Yes |  | 多头涨幅 - 空头涨幅 |
| spread_5d | decimal(10,6) | Yes |  | 5日累计差值 |
| spread_20d | decimal(10,6) | Yes |  |  |
| direction | varchar(20) | Yes |  | long_dominant/short_dominant |
| created_at | timestamp | No |  |  |

---

### 表: `ads_l2_style_rotation`
- **描述**: 无备注
- **行数**: 34
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| ts_code | varchar(20) | Yes |  |  |
| name | varchar(50) | No | PRI |  |
| pct_chg | decimal(8,4) | Yes |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `ads_l8_unified_signal`
- **描述**: ADS-异动信号统一池
- **行数**: 0
- **占用空间**: 0.06 MB (数据: 0.02MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| user_id | bigint(20) unsigned | No | MUL |  |
| trade_date | date | No | MUL |  |
| ts_code | varchar(20) | No | MUL |  |
| name | varchar(50) | No |  |  |
| industry_sw1 | varchar(50) | Yes |  |  |
| industry_sw3 | varchar(50) | Yes |  |  |
| pool_type | varchar(16) | No |  | strong/early/trap |
| signal_type | varchar(40) | No |  |  |
| signal_subtype | varchar(40) | Yes |  |  |
| pct_chg | decimal(10,6) | Yes |  |  |
| turnover_rate | decimal(10,6) | Yes |  |  |
| volume_ratio_5d | decimal(10,6) | Yes |  |  |
| amount | decimal(20,2) | Yes |  |  |
| main_net_inflow | decimal(20,2) | Yes |  |  |
| signal_features | json | Yes |  | 差异化指标 |
| tags | json | Yes |  | 多维度标签 |
| resonance_level | tinyint(4) | Yes |  | 共振等级 1-5 |
| resonance_dimensions | json | Yes |  | 共振维度详情 |
| resonance_score | decimal(6,2) | Yes |  |  |
| counter_signals | json | Yes |  | 反向信号 |
| counter_signal_score | decimal(6,2) | Yes |  |  |
| temporal_resonance | json | Yes |  | 时间窗口共振 |
| raw_score | decimal(6,2) | Yes |  |  |
| score_l3_capital | decimal(6,2) | Yes |  |  |
| score_l4_emotion | decimal(6,2) | Yes |  |  |
| score_user_pref | decimal(6,2) | Yes |  |  |
| score_dedup_pen | decimal(6,2) | Yes |  |  |
| composite_score | decimal(6,2) | Yes |  | 综合评分 |
| excluded_reasons | json | Yes |  | 排除理由 |
| default_visible | tinyint(1) | Yes |  |  |
| explanation_zh | varchar(500) | Yes |  | 中文解释 |
| extra | json | Yes |  |  |
| schema_version | varchar(10) | Yes |  |  |
| compute_version | varchar(20) | Yes |  |  |
| is_deleted | tinyint(1) | Yes |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `ads_market_state_daily`
- **描述**: ADS-市场状态
- **行数**: 0
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| is_normal | tinyint(1) | Yes |  |  |
| csi300_pct_chg | decimal(10,6) | Yes |  |  |
| abnormal_reasons | json | Yes |  |  |
| signal_reliability | decimal(4,2) | Yes |  | 可信度系数 0-1 |
| manual_override | tinyint(1) | Yes |  |  |
| note | varchar(200) | Yes |  |  |
| extra | json | Yes |  |  |
| schema_version | varchar(10) | Yes |  |  |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `ads_stock_derived_metrics`
- **描述**: ADS-派生指标层
- **行数**: 0
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI | 交易日 |
| ts_code | varchar(20) | No | PRI | 股票代码 |
| volume_ratio_5d | decimal(10,4) | Yes |  | 5 日量比均值 |
| volume_ratio_20d | decimal(10,4) | Yes |  | 20 日量比均值 |
| vol_5d_to_60d | decimal(10,4) | Yes |  | 5 日均量 / 60 日均量 |
| vol_consistency_days | tinyint(4) | Yes |  | 连续满足量比 ∈ [1.5,2.5] 的天数 |
| cumulative_5d_pct | decimal(10,6) | Yes |  | 5 日累计涨跌幅 |
| cumulative_20d_pct | decimal(10,6) | Yes |  | 20 日累计涨跌幅 |
| cumulative_60d_pct | decimal(10,6) | Yes |  | 60 日累计涨跌幅 |
| amplitude_today | decimal(10,6) | Yes |  | 当日振幅 |
| amplitude_10d | decimal(10,6) | Yes |  | 10 日总振幅 |
| industry_rank_pct_today | decimal(6,4) | Yes |  | 行业内涨幅分位(0=最强) |
| industry_rank_pct_avg_5d | decimal(6,4) | Yes |  | 前 5 日行业内分位均值 |
| capital_rank_today | int(11) | Yes |  | 主力净流入全市场排名 |
| capital_rank_avg_5d | decimal(8,2) | Yes |  | 前 5 日主力排名均值 |
| dist_to_ma5 | decimal(10,6) | Yes |  | 与 MA5 的乖离率 |
| dist_to_ma10 | decimal(10,6) | Yes |  | 与 MA10 的乖离率 |
| dist_to_ma20 | decimal(10,6) | Yes |  | 与 MA20 的乖离率 |
| dist_to_ma60 | decimal(10,6) | Yes |  | 与 MA60 的乖离率 |
| dist_to_ma250 | decimal(10,6) | Yes |  | 与 MA250 的乖离率 |
| ma_convergence | decimal(10,6) | Yes |  | 均线粘合度 |
| box_test_count_60d | tinyint(4) | Yes |  | 60 日内压力位测试次数 |
| box_resistance_level | decimal(16,4) | Yes |  | 识别出的压力位价格 |
| is_first_recovery_ma250 | tinyint(1) | Yes |  | 是否首次站稳 MA250 |
| extra_metrics | json | Yes |  |  |
| schema_version | varchar(10) | Yes |  |  |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `monitor_health_scores`
- **描述**: 无备注
- **行数**: 6,292
- **占用空间**: 0.27 MB (数据: 0.27MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| total_score | double | Yes |  |  |
| status | varchar(20) | Yes |  |  |

---

### 表: `monitor_indicators_history`
- **描述**: 无备注
- **行数**: 24,016
- **占用空间**: 5.53 MB (数据: 2.50MB, 索引: 3.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| indicator_name | varchar(50) | No | PRI |  |
| indicator_value | double | Yes |  |  |
| score | double | Yes |  |  |

---

## 系统审计与元数据 (System & Metadata)

### 表: `commands`
- **描述**: 无备注
- **行数**: 5
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| task_id | varchar(50) | No |  |  |
| params | json | Yes |  |  |
| status | varchar(20) | Yes |  |  |
| result | text | Yes |  |  |
| created_at | datetime | Yes |  |  |
| executed_at | datetime | Yes |  |  |
| finished_at | datetime | Yes |  |  |
| request_id | varchar(50) | Yes |  |  |

---

### 表: `data_audit_details`
- **描述**: 数据校验详情明细表
- **行数**: 55
- **占用空间**: 0.23 MB (数据: 0.22MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI | 自增主键 |
| summary_id | bigint(20) | No | MUL | 关联汇总ID |
| dimension | varchar(64) | No |  | 校验维度: availability, continuity, price... |
| level | varchar(16) | No |  | 问题级别: PASS, WARN, FAIL |
| message | varchar(512) | Yes |  | 具体问题描述 |
| context | json | Yes |  | 上下文数据(JSON) |
| created_at | datetime | Yes |  | 创建时间 |

---

### 表: `data_audit_summaries`
- **描述**: 数据校验结果汇总表
- **行数**: 13
- **占用空间**: 0.06 MB (数据: 0.02MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI | 自增主键 |
| data_type | varchar(32) | No | MUL | 数据类型: tick, kline, market |
| target | varchar(64) | No |  | 校验目标: 股票代码或日期(YYYY-MM-DD) |
| trade_date | date | No | MUL | 业务交易日期 |
| level | varchar(16) | No | MUL | 校验结果级别: PASS, WARN, FAIL |
| issue_count | int(11) | Yes |  | 问题总数 |
| description | varchar(255) | Yes |  | 结果简述 |
| created_at | datetime | Yes |  | 创建时间 |
| updated_at | datetime | Yes |  | 更新时间 |

---

### 表: `data_gate_audits`
- **描述**: 精简版数据门禁每日审计历史
- **行数**: 55
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| trade_date | date | No | MUL | 交易日期 |
| gate_id | varchar(20) | No |  | GATE_1/2/3 |
| is_complete | tinyint(1) | No |  | 1: 完整, 0: 不完整 |
| description | varchar(255) | Yes |  | 简要结果说明 |
| created_at | datetime | Yes |  |  |

---

### 表: `migrations_history`
- **描述**: 无备注
- **行数**: 6
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| migration_name | varchar(255) | No | UNI |  |
| applied_at | datetime | Yes |  |  |

---

## 股市日记与盘后复盘 (Diary & Market Review)

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

### 表: `diary_stock`
- **描述**: 日记股票关联
- **行数**: 8
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
- **行数**: 8
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

### 表: `fupan_data`
- **描述**: 复盘数据表
- **行数**: 0
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI | 主键ID |
| date | date | No | UNI | 复盘日期（唯一） |
| comprehensive_description | text | Yes |  | 大盘整体走势描述（如趋势、情绪、量能等） |
| index_change | text | Yes |  | 主要指数涨跌幅及走势分析（如上证、深成指、创业板等） |
| top_concept_changes | text | Yes |  | 当日热门概念板块变化及涨幅情况总述 |
| concept_1_name | varchar(100) | Yes |  | 第一热门概念板块名称 |
| concept_1_change | varchar(20) | Yes |  | 第一热门概念板块涨跌幅（如 +5.2%） |
| concept_2_name | varchar(100) | Yes |  | 第二热门概念板块名称 |
| concept_2_change | varchar(20) | Yes |  | 第二热门概念板块涨跌幅（如 +4.8%） |
| concept_3_name | varchar(100) | Yes |  | 第三热门概念板块名称 |
| concept_3_change | varchar(20) | Yes |  | 第三热门概念板块涨跌幅（如 +4.1%） |
| main_highlights | text | Yes |  | 当日市场主要亮点（如龙头股、政策影响、热点事件等） |
| stock_activity | text | Yes |  | 个股活跃度分析（如涨停/跌停数量、换手率、成交量等） |
| sealing_efficiency | text | Yes |  | 封板效率分析（涨停封板率、炸板情况等） |
| created_at | timestamp | No |  | 记录创建时间 |

---

## 其他与备份 (Others/Legacy)

### 表: `anal_result`
- **描述**: 无备注
- **行数**: 21,280
- **占用空间**: 96.56 MB (数据: 96.56MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| anal_type | int(11) | No | PRI |  |
| anal_name | varchar(100) | Yes |  |  |
| ts_code_list | text | Yes |  |  |
| stock_count | int(11) | Yes |  |  |

---

### 表: `app_anomaly_top10_daily`
- **描述**: APP-每日 Top 10 推送清单
- **行数**: 0
- **占用空间**: 0.06 MB (数据: 0.02MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| user_id | bigint(20) unsigned | No | MUL |  |
| trade_date | date | No | MUL |  |
| rank_no | tinyint(4) | No |  |  |
| signal_id | bigint(20) unsigned | No | MUL |  |
| ts_code | varchar(20) | No |  |  |
| name | varchar(50) | No |  |  |
| industry_sw1 | varchar(50) | Yes |  |  |
| pool_type | varchar(16) | No |  |  |
| signal_type | varchar(40) | No |  |  |
| signal_subtype | varchar(40) | Yes |  |  |
| composite_score | decimal(6,2) | No |  |  |
| resonance_level | tinyint(4) | Yes |  |  |
| quota_slot | varchar(20) | No |  | quota_strong/early/trap/filled/l5_must |
| profile_code | varchar(40) | Yes |  |  |
| headline | varchar(200) | Yes |  |  |
| key_features | json | Yes |  |  |
| extra | json | Yes |  |  |
| schema_version | varchar(10) | Yes |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `CCI_alerts`
- **描述**: 无备注
- **行数**: 0
- **占用空间**: 0.05 MB (数据: 0.02MB, 索引: 0.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| stock_code | varchar(20) | No | MUL |  |
| alert_date | datetime | No | MUL |  |
| layer | varchar(10) | No |  |  |
| alert_type | varchar(20) | No |  | 预警类型: CRITICAL_SLOWING, DISLOCATION |
| severity | varchar(10) | No |  |  |
| message | text | No |  |  |
| meta_data | json | Yes |  |  |
| is_read | tinyint(1) | No |  |  |
| created_at | datetime | No |  |  |

---

### 表: `CCI_dislocations`
- **描述**: 无备注
- **行数**: 0
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| trade_date | datetime | No | MUL |  |
| base_layer | varchar(10) | No |  | 基准层级 |
| target_layer | varchar(10) | No |  | 对比层级 |
| dislocation_score | float | No |  | 错位分值 |
| direction | int(11) | No |  | 方向: 1(向上错位), -1(向下错位) |
| created_at | datetime | No |  |  |

---

### 表: `CCI_records`
- **描述**: 无备注
- **行数**: 0
- **占用空间**: 0.08 MB (数据: 0.02MB, 索引: 0.06MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| stock_code | varchar(20) | No | MUL | 股票/指数代码 |
| trade_date | datetime | No | MUL | 交易日期 |
| cci_value | float | No |  | CCI 计算值 |
| rho_value | float | No |  | 横截面相关性 Rho |
| var_value | float | No |  | 方差 Var |
| layer | varchar(10) | No | MUL | 监测层级 L1-L6 |
| is_critical | tinyint(1) | No |  | 是否处于临界状态 |
| created_at | datetime | No |  |  |

---

### 表: `data_quality_reports`
- **描述**: 无备注
- **行数**: 1
- **占用空间**: 0.05 MB (数据: 0.02MB, 索引: 0.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| report_type | varchar(20) | No | MUL |  |
| overall_status | varchar(20) | No |  |  |
| check_time | datetime | No | MUL |  |
| report_content | json | No |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `dim_anomaly_score_weight`
- **描述**: DIM-评分权重配置
- **行数**: 14
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| version | varchar(20) | No | PRI |  |
| weight_key | varchar(40) | No | PRI |  |
| weight_value | decimal(6,4) | No |  |  |
| weight_desc | varchar(200) | Yes |  |  |
| is_active | tinyint(1) | Yes |  |  |
| effective_from | date | Yes |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `dim_filter_profile`
- **描述**: DIM-筛选模板
- **行数**: 5
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| profile_code | varchar(40) | No | PRI |  |
| profile_name | varchar(50) | No |  |  |
| description | varchar(200) | Yes |  |  |
| rules_json | json | No |  |  |
| is_system | tinyint(1) | Yes |  |  |
| display_order | int(11) | Yes |  |  |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `dim_style_factor`
- **描述**: DIM: 风格因子定义
- **行数**: 4
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| factor_code | varchar(30) | No | PRI | 因子代码, 如 large_vs_small |
| factor_name | varchar(50) | Yes |  | 因子中文名, 如 大小盘强弱 |
| long_index | varchar(20) | Yes |  | 多头指数代码 (对应 index_basic) |
| long_name | varchar(50) | Yes |  | 多头指数名称 |
| short_index | varchar(20) | Yes |  | 空头指数代码 (对应 index_basic) |
| short_name | varchar(50) | Yes |  | 空头指数名称 |
| description | varchar(200) | Yes |  | 因子说明 |
| display_order | int(11) | Yes |  | 展示顺序 |
| is_active | tinyint(1) | Yes | MUL | 是否启用 |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `dim_tag_dictionary`
- **描述**: DIM-标签字典
- **行数**: 58
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| tag_code | varchar(40) | No | PRI |  |
| tag_name_cn | varchar(50) | No |  |  |
| tag_category | varchar(20) | No |  |  |
| tag_subcategory | varchar(20) | Yes |  |  |
| tag_description | varchar(200) | Yes |  |  |
| display_order | int(11) | Yes |  |  |
| is_active | tinyint(1) | Yes |  |  |
| tag_meta | json | Yes |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `dim_tag_relation`
- **描述**: DIM-标签关系
- **行数**: 9
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| tag_a | varchar(40) | No | PRI |  |
| tag_b | varchar(40) | No | PRI |  |
| relation_type | varchar(20) | No | PRI | mutex/imply/correlate |

---

### 表: `dim_user_active_profile`
- **描述**: DIM-用户当前激活模板
- **行数**: 1
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| user_id | bigint(20) unsigned | No | PRI |  |
| profile_code | varchar(40) | No |  |  |
| is_active | tinyint(1) | Yes |  |  |
| activated_at | timestamp | No |  |  |

---

### 表: `dim_user_sector_pref`
- **描述**: DIM-用户板块偏好
- **行数**: 0
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| user_id | bigint(20) unsigned | No | MUL |  |
| sector_type | varchar(16) | No |  | industry_sw1/concept |
| sector_code | varchar(50) | No |  |  |
| sector_name | varchar(50) | No |  |  |
| weight | decimal(4,2) | No |  |  |
| is_active | tinyint(1) | No |  |  |
| extra | json | Yes |  |  |
| schema_version | varchar(10) | Yes |  |  |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `index_basic`
- **描述**: DIM:指数维表(Tushare index_basic 同步)
- **行数**: 7,935
- **占用空间**: 2.14 MB (数据: 1.52MB, 索引: 0.62MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI | 指数代码,如 000300.SH |
| name | varchar(100) | Yes |  | 指数简称,如 沪深300 |
| fullname | varchar(200) | Yes |  | 指数全称 |
| market | varchar(20) | Yes |  | 市场,如 SSE/SZSE/CSI/SW |
| publisher | varchar(50) | Yes |  | 发布方 |
| index_type | varchar(50) | Yes |  | 指数风格 |
| category | varchar(50) | Yes | MUL | 指数类别(综合/规模/行业/主题/风格/策略/基金/债券) |
| base_date | date | Yes |  | 基期 |
| base_point | decimal(16,4) | Yes |  | 基点 |
| list_date | date | Yes |  | 发布日期 |
| weight_rule | varchar(50) | Yes |  | 加权方式 |
| description | text | Yes |  | 描述 |
| exp_date | date | Yes |  | 终止日期(NULL 表示有效) |
| is_core | tinyint(1) | Yes | MUL | 是否核心指数(1=是,0=否),L1 看板只展示核心 |
| display_order | int(11) | Yes |  | 展示顺序(越小越靠前) |
| data_source | varchar(20) | Yes |  | 数据源 |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `log_signal_lifecycle`
- **描述**: LOG-信号生命周期
- **行数**: 0
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| original_id | bigint(20) unsigned | No | MUL | 关联统一信号表 id |
| tracked_date | date | No |  |  |
| state | varchar(20) | No |  | active/continuing/reversed/failed |
| state_features | json | Yes |  |  |
| delta_metrics | json | Yes |  | 相对触发日的变化指标 |
| extra | json | Yes |  |  |
| schema_version | varchar(10) | Yes |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `mootdx_symbol`
- **描述**: 无备注
- **行数**: 25,795
- **占用空间**: 2.52 MB (数据: 2.52MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| code | char(6) | No | PRI | 股票代码 |
| name | char(50) | No |  | 股票名称 |
| pre_close | decimal(8,2) | Yes |  | 昨日收盘 |

---

### 表: `mp_account`
- **描述**: 公众号授权账户
- **行数**: 1
- **占用空间**: 0.06 MB (数据: 0.02MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| user_id | bigint(20) unsigned | No | MUL | 所属系统用户 |
| mp_appid | varchar(64) | No | MUL | 公众号 AppID |
| mp_appsecret | varchar(128) | Yes |  |  |
| mp_name | varchar(64) | Yes |  |  |
| mp_avatar | varchar(512) | Yes |  |  |
| mp_type | tinyint(4) | No |  | 1=订阅号 2=服务号 3=认证订阅号 4=认证服务号 |
| mp_original_id | varchar(64) | Yes |  | 公众号原始 ID gh_xxx |
| access_token_encrypted | varchar(512) | Yes |  |  |
| access_token_expires_at | datetime | Yes |  |  |
| refresh_token_encrypted | varchar(512) | Yes |  |  |
| authorizer_refresh_token | varchar(512) | Yes |  | 第三方平台授权时使用 |
| scope | varchar(255) | Yes |  | 授权范围,JSON 字符串 |
| status | tinyint(4) | No |  | 0=已解绑 1=正常 2=授权过期 3=被封禁 |
| is_default | tinyint(1) | No |  | 是否设为默认发布账号 |
| authorized_at | datetime | Yes |  |  |
| last_used_at | datetime | Yes |  |  |
| created_at | datetime | No |  |  |
| updated_at | datetime | No |  |  |

---

### 表: `mp_media_cache`
- **描述**: 微信素材库缓存
- **行数**: 0
- **占用空间**: 0.05 MB (数据: 0.02MB, 索引: 0.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| mp_account_id | bigint(20) unsigned | No | MUL |  |
| cos_key | varchar(255) | No |  | 本地 COS 对象 key |
| media_type | varchar(16) | No |  | image/voice/video/thumb |
| wx_media_id | varchar(128) | No |  |  |
| wx_media_url | varchar(512) | Yes |  |  |
| last_used_at | datetime | Yes | MUL | 最近使用时间,用于 LRU 清理 |
| use_count | int(10) unsigned | No |  |  |
| created_at | datetime | No |  |  |

---

### 表: `mp_publish_record`
- **描述**: 公众号发布记录
- **行数**: 81
- **占用空间**: 0.20 MB (数据: 0.14MB, 索引: 0.06MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| user_id | bigint(20) unsigned | No | MUL |  |
| diary_id | bigint(20) unsigned | No | MUL | 源日记 |
| mp_account_id | bigint(20) unsigned | No | MUL | 发布到的公众号 |
| title | varchar(128) | No |  |  |
| author | varchar(64) | Yes |  |  |
| digest | varchar(255) | Yes |  | 摘要,公众号图文必填 |
| content_html | mediumtext | No |  | 发布到公众号的最终 HTML |
| content_source_url | varchar(512) | Yes |  | 原文链接,可空 |
| cover_attachment_id | bigint(20) unsigned | Yes |  | 封面附件 |
| cover_wx_media_id | varchar(128) | Yes |  | 封面在微信侧的素材 ID |
| show_cover_pic | tinyint(1) | No |  |  |
| need_open_comment | tinyint(1) | No |  |  |
| wx_media_id | varchar(128) | Yes | MUL | 图文素材 media_id |
| wx_publish_id | varchar(128) | Yes |  | 发布任务 publish_id |
| wx_msg_data_id | varchar(128) | Yes |  | 已发图文的 msg_data_id |
| wx_article_url | varchar(512) | Yes |  | 已发图文的访问 URL |
| status | tinyint(4) | No |  | 0=草稿 1=已上传素材 2=已发布 3=已撤回 4=失败 |
| error_code | varchar(32) | Yes |  |  |
| error_message | varchar(512) | Yes |  |  |
| uploaded_at | datetime | Yes |  | 素材上传完成时间 |
| published_at | datetime | Yes |  | 发布完成时间 |
| created_at | datetime | No |  |  |
| updated_at | datetime | No |  |  |
| deleted_at | datetime | Yes |  |  |

---

### 表: `north_capital_daily`
- **描述**: ODS:北向资金每日净流入(2024-08 后港交所仅披露日终)
- **行数**: 2,649
- **占用空间**: 0.12 MB (数据: 0.12MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| north_net_inflow | decimal(20,2) | Yes |  | 北向资金当日净流入(元) |
| updated_at | timestamp | No |  |  |

---

### 表: `raw_capital_flow_summary`
- **描述**: 无备注
- **行数**: 0
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| north_net_inflow | decimal(20,4) | Yes |  |  |
| south_net_inflow | decimal(20,4) | Yes |  |  |

---

### 表: `raw_market_stats`
- **描述**: 无备注
- **行数**: 0
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No | PRI |  |
| advance_count | int(11) | Yes |  | 上涨家数 |
| decline_count | int(11) | Yes |  | 下跌家数 |
| total_market_cap | decimal(20,2) | Yes |  | 全市场总市值 |
| avg_turnover | decimal(10,4) | Yes |  | 平均换手率 |
| updated_at | timestamp | No |  |  |

---

### 表: `raw_sector_daily`
- **描述**: 无备注
- **行数**: 0
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI |  |
| trade_date | date | No | PRI |  |
| open | decimal(16,4) | Yes |  |  |
| high | decimal(16,4) | Yes |  |  |
| low | decimal(16,4) | Yes |  |  |
| close | decimal(16,4) | Yes |  |  |
| volume | decimal(20,4) | Yes |  |  |
| amount | decimal(20,4) | Yes |  |  |

---

### 表: `sector_kline_daily`
- **描述**: ODS:行业 / ETF 日线行情
- **行数**: 141,851
- **占用空间**: 20.55 MB (数据: 13.52MB, 索引: 7.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 行业代码或ETF代码 |
| trade_date | date | No | MUL |  |
| open | decimal(16,4) | Yes |  |  |
| high | decimal(16,4) | Yes |  |  |
| low | decimal(16,4) | Yes |  |  |
| close | decimal(16,4) | Yes |  |  |
| volume | decimal(20,2) | Yes |  |  |
| amount | decimal(20,2) | Yes |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_adjust_factor`
- **描述**: 股票复权因子表
- **行数**: 74,189
- **占用空间**: 13.58 MB (数据: 5.52MB, 索引: 8.06MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(16) | Yes | MUL |  |
| adjust_date | date | No | MUL | 除权除息日期 |
| fore_adjust_factor | decimal(16,6) | Yes |  | 前复权因子 |
| back_adjust_factor | decimal(16,6) | Yes |  | 后复权因子 |
| adjust_factor | decimal(16,6) | Yes |  | 复权因子 |
| created_at | timestamp | No |  | 入库时间 |

---

### 表: `stock_analyst_rank`
- **描述**: 机构评级记录表
- **行数**: 238
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | Yes | MUL |  |
| report_date | date | No |  |  |
| analyst | varchar(50) | No |  | 机构/分析师名称 |
| rating | varchar(20) | No |  | 评级 (买入/增持/中性) |
| change_direction | varchar(10) | Yes |  | 变动 (维持/调高/调低) |
| target_price | decimal(10,2) | Yes |  | 目标价 |
| created_at | timestamp | No |  |  |

---

### 表: `stock_basic_info`
- **描述**: 无备注
- **行数**: 5,928
- **占用空间**: 1.52 MB (数据: 1.52MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI | TS代码 |
| symbol | varchar(10) | Yes |  | 股票代码 |
| name | varchar(100) | Yes |  | 股票名称 |
| area | varchar(50) | Yes |  | 地域 |
| industry | varchar(50) | Yes |  | 所属行业 |
| fullname | varchar(200) | Yes |  | 股票全称 |
| enname | varchar(200) | Yes |  | 英文全称 |
| cnspell | varchar(20) | Yes |  | 拼音缩写 |
| market | varchar(20) | Yes |  | 市场类型（主板/创业板/科创板/CDR） |
| exchange | varchar(20) | Yes |  | 交易所代码 |
| curr_type | varchar(10) | Yes |  | 交易货币 |
| list_status | varchar(10) | Yes |  | 上市状态 L上市 D退市 P暂停上市 |
| list_date | date | Yes |  | 上市日期 |
| delist_date | date | Yes |  | 退市日期 |
| is_hs | varchar(1) | Yes |  | 是否沪深港通标的，N否 H沪股通 S深股通 |
| act_name | varchar(100) | Yes |  | 实控人名称 |
| act_ent_type | varchar(50) | Yes |  | 实控人企业性质 |
| issue_price | decimal(10,2) | Yes |  | 发行价格 |
| finance_sync_time | datetime | Yes |  | 最后一次成功同步全量财务数据的时间 |

---

### 表: `stock_block_trade`
- **描述**: 大宗交易表
- **行数**: 298,162
- **占用空间**: 69.59 MB (数据: 54.08MB, 索引: 15.52MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| trade_date | date | No | MUL | 交易日期 |
| price | decimal(10,4) | Yes |  | 成交价 |
| volume | bigint(20) | Yes |  | 成交量 |
| amount | decimal(20,2) | Yes |  | 成交额 |
| buyer | varchar(255) | Yes |  | 买方营业部 |
| seller | varchar(255) | Yes |  | 卖方营业部 |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_health_ledger`
- **描述**: 无备注
- **行数**: 100
- **占用空间**: 0.05 MB (数据: 0.02MB, 索引: 0.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| stock_code | varchar(20) | No | PRI |  |
| status | varchar(10) | No | MUL |  |
| listing_date | date | Yes |  |  |
| missing_count | int(11) | Yes |  |  |
| missing_details | json | Yes |  |  |
| suspension_count | int(11) | Yes |  |  |
| last_scan_time | datetime | Yes | MUL |  |
| repair_status | int(11) | Yes |  |  |
| created_at | timestamp | No |  |  |

---

### 表: `stock_industry_em`
- **描述**: 东方财富行业分类表
- **行数**: 0
- **占用空间**: 0.06 MB (数据: 0.02MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 (如 600519.SH) |
| industry_code | varchar(20) | No | MUL | 东方财富行业代码 (如 BK0473) |
| industry_name | varchar(50) | No |  | 东方财富行业名称 (如 半导体) |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_industry_sw`
- **描述**: 申万行业分类明细
- **行数**: 4,622
- **占用空间**: 2.19 MB (数据: 1.52MB, 索引: 0.67MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| code | varchar(20) | No | PRI | 标准股票代码 |
| l1_code | varchar(20) | Yes | MUL | 一级行业代码 |
| l1_name | varchar(50) | Yes |  | 一级行业名称 |
| l2_code | varchar(20) | Yes | MUL | 二级行业代码 |
| l2_name | varchar(50) | Yes |  | 二级行业名称 |
| l3_code | varchar(20) | Yes | MUL | 三级行业代码 |
| l3_name | varchar(50) | Yes |  | 三级行业名称 |
| update_time | datetime | Yes |  |  |

---

### 表: `stock_industry_ths`
- **描述**: 同花顺行业分类表 (L1/L2/L3)
- **行数**: 5,579
- **占用空间**: 1.17 MB (数据: 0.45MB, 索引: 0.72MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | UNI | 股票代码 (如 600519.SH) |
| l1_name | varchar(50) | Yes | MUL | 同花顺一级行业 |
| l2_name | varchar(50) | Yes | MUL | 同花顺二级行业 |
| l3_name | varchar(50) | Yes | MUL | 同花顺三级行业 |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_info`
- **描述**: 股票主数据
- **行数**: 23
- **占用空间**: 0.09 MB (数据: 0.02MB, 索引: 0.08MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI |  |
| ts_code | varchar(16) | No | UNI | 完整代码,如 600519.SH |
| symbol | varchar(10) | No | MUL | 纯数字代码 |
| name | varchar(32) | No |  | 当前名称 |
| name_alias | varchar(255) | Yes |  | 曾用名,逗号分隔 |
| pinyin | varchar(64) | Yes |  | 全拼 |
| pinyin_initial | varchar(16) | Yes | MUL | 首字母 |
| market | varchar(8) | No |  | SH/SZ/BJ/HK/US |
| board | varchar(16) | Yes |  | 主板/创业板/科创板/北交所 |
| industry_sw | varchar(32) | Yes | MUL | 申万一级行业 |
| industry_sw2 | varchar(32) | Yes |  | 申万二级行业 |
| list_date | date | Yes |  |  |
| delist_date | date | Yes |  |  |
| status | tinyint(4) | No | MUL | 1=正常 0=退市 2=停牌 3=ST |
| meta | json | Yes |  |  |
| created_at | datetime | No |  |  |
| updated_at | datetime | No |  |  |

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
| close_price | decimal(10,4) | Yes |  | 收盘价 |
| change_pct | decimal(10,4) | Yes |  | 涨跌幅 |
| turnover_rate | decimal(10,4) | Yes |  | 换手率 |
| net_buy_amt | decimal(20,2) | Yes |  | 龙虎榜净买入额 |
| buy_amt | decimal(20,2) | Yes |  | 龙虎榜买入额 |
| sell_amt | decimal(20,2) | Yes |  | 龙虎榜卖出额 |
| turnover_amt | decimal(20,2) | Yes |  | 龙虎榜成交额 |
| reason | text | Yes |  | 上榜原因 |
| inst_net_buy_amt | decimal(20,2) | Yes |  | 机构净买入额 |
| inst_buy_amt | decimal(20,2) | Yes |  | 机构买入额 |
| inst_sell_amt | decimal(20,2) | Yes |  | 机构卖出额 |
| inst_buy_count | int(11) | Yes |  | 买入机构数 |
| inst_sell_count | int(11) | Yes |  | 卖出机构数 |
| updated_at | timestamp | No |  |  |

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
| hold_count | bigint(20) | Yes |  | 持股数量 |
| hold_market_cap | decimal(20,2) | Yes |  | 持股市值 |
| hold_ratio | decimal(10,4) | Yes |  | 持股占比(%) |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_performance_forecast`
- **描述**: 业绩预告表
- **行数**: 29,420
- **占用空间**: 8.03 MB (数据: 6.52MB, 索引: 1.52MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| report_period | date | No |  | 报告期 |
| notice_date | date | No |  | 公告日期 |
| type | varchar(255) | Yes |  | 业绩变动类型 |
| growth_min | decimal(16,4) | Yes |  |  |
| growth_max | decimal(16,4) | Yes |  |  |
| growth_range | varchar(255) | Yes |  | 预告幅度 |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_restricted_release`
- **描述**: 限售股解禁表
- **行数**: 43,110
- **占用空间**: 9.06 MB (数据: 4.52MB, 索引: 4.55MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| release_date | date | No | MUL | 解禁日期 |
| release_count | bigint(20) | Yes |  | 解禁数量 |
| release_market_cap | decimal(20,2) | Yes |  | 解禁市值 |
| ratio | decimal(10,4) | Yes |  | 占总股本比例 |
| holder_type | varchar(255) | Yes |  | 解禁股本类型 |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_sector_cons_ths`
- **描述**: 同花顺板块成分映射
- **行数**: 69,622
- **占用空间**: 12.06 MB (数据: 3.52MB, 索引: 8.55MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| sector_id | int(11) | No | MUL | 板块ID |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_sector_ths`
- **描述**: 同花顺板块字典
- **行数**: 736
- **占用空间**: 0.11 MB (数据: 0.06MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| sector_name | varchar(50) | No | MUL | 板块名称 |
| sector_type | enum('industry','concept') | No |  | 板块类型 |
| sector_level | varchar(10) | Yes |  | 级别 (仅限行业: L1/L2/L3) |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_sentiment_daily`
- **描述**: 每日市场热度统计
- **行数**: 1
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | Yes | MUL |  |
| trade_date | date | No |  |  |
| post_count | int(11) | Yes |  | 当日发帖数 |
| read_count | int(11) | Yes |  | 当日阅读数 |
| comment_count | int(11) | Yes |  | 当日评论数 |
| rank_score | int(11) | Yes |  | 股吧热度排名(如有) |

---

### 表: `stock_suspensions`
- **描述**: 股票每日停牌记录
- **行数**: 3,732
- **占用空间**: 0.58 MB (数据: 0.22MB, 索引: 0.36MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| trade_date | date | No | MUL | 停牌日期 |
| is_suspended | tinyint(1) | Yes |  | 是否停牌 1=是 |
| reason | varchar(255) | Yes |  | 停牌原因(如有) |
| created_at | timestamp | No |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `stock_xr_schedules`
- **描述**: 除权除息日程表
- **行数**: 0
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| ts_code | varchar(20) | No | MUL | 股票代码 |
| ex_date | date | No |  | 除权除息日 |
| bonus_ratio | decimal(10,4) | Yes |  | 送转比例 |
| cash_div | decimal(10,4) | Yes |  | 每股派现 |
| created_at | timestamp | No |  |  |

---

### 表: `sync_execution_logs`
- **描述**: 本地任务执行日志表
- **行数**: 453
- **占用空间**: 0.11 MB (数据: 0.09MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| task_name | varchar(50) | No | MUL | 任务名称 |
| execution_time | datetime | No |  | 执行时间 |
| status | varchar(20) | No |  | 状态: SUCCESS, FAILED, RUNNING |
| records_processed | int(11) | Yes |  | 同步/处理记录数 |
| details | text | Yes |  | 详细日志信息 |
| duration_seconds | float | Yes |  | 耗时(秒) |

---

### 表: `sync_progress`
- **描述**: 无备注
- **行数**: 1
- **占用空间**: 0.03 MB (数据: 0.02MB, 索引: 0.02MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| task_name | varchar(64) | Yes | UNI |  |
| current_code | varchar(16) | Yes |  |  |
| last_index | int(11) | Yes |  |  |
| total_count | int(11) | Yes |  |  |
| status | varchar(20) | Yes |  |  |
| updated_at | timestamp | No |  |  |

---

### 表: `sys_user`
- **描述**: 用户主表
- **行数**: 4
- **占用空间**: 0.09 MB (数据: 0.02MB, 索引: 0.08MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) unsigned | No | PRI | 主键 |
| openid | varchar(64) | No | UNI | 微信小程序 openid |
| unionid | varchar(64) | Yes | MUL | 微信开放平台 unionid,关联公众号必备 |
| phone_encrypted | varchar(255) | Yes |  | 手机号 AES 加密密文 |
| phone_hash | char(64) | Yes | MUL | 手机号 SHA256,用于精确查询 |
| email | varchar(128) | Yes |  | 兜底邮箱 |
| nickname | varchar(64) | Yes |  | 昵称 |
| avatar_url | varchar(512) | Yes |  | 头像 URL |
| gender | tinyint(4) | No |  | 0=未知 1=男 2=女 |
| region | varchar(64) | Yes |  | 地区 |
| status | tinyint(4) | No | MUL | 1=正常 0=已注销 -1=风控封禁 |
| level | tinyint(4) | No |  | 0=普通 1=试用 2=付费 9=内测 |
| expired_at | datetime | Yes |  | 会员到期时间 |
| banned_until | datetime | Yes |  | 封禁到期,NULL=未封禁 |
| quota_diary | int(10) unsigned | Yes |  | 日记总数上限 |
| quota_storage_mb | int(10) unsigned | Yes |  | 附件存储 MB 上限 |
| quota_watchlist | int(10) unsigned | Yes |  | 自选股数量上限 |
| quota_mp_account | tinyint(3) unsigned | Yes |  | 可绑定公众号数量上限 |
| prefs | json | Yes |  | 用户偏好,通知/UI/默认值等 |
| diary_count | int(10) unsigned | No |  | 日记总数 |
| storage_used_kb | bigint(20) unsigned | No |  | 附件已用存储 KB |
| risk_level | tinyint(4) | No |  | 0=正常 1=可疑 2=高危 |
| last_login_ip | varchar(45) | Yes |  | IPv4/IPv6 |
| last_login_at | datetime | Yes |  |  |
| last_active_at | datetime | Yes | MUL | 最近活跃时间 |
| meta | json | Yes |  | 临时扩展字段 |
| created_at | datetime | No |  |  |
| updated_at | datetime | No |  |  |
| deleted_at | datetime | Yes |  | 软删除时间 |

---

### 表: `task_commands`
- **描述**: 异步任务命令队列
- **行数**: 531
- **占用空间**: 14.58 MB (数据: 14.52MB, 索引: 0.06MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| run_id | char(36) | Yes | MUL |  |
| step_id | varchar(100) | Yes |  |  |
| task_id | varchar(100) | No |  | 任务ID，如 pre_market_gate |
| params | json | Yes |  | 可选参数，如 {"target_date": "20260113"} |
| input_context | json | Yes |  |  |
| status | enum('PENDING','RUNNING','DONE','FAILED') | Yes | MUL |  |
| created_at | datetime | Yes |  |  |
| executed_at | datetime | Yes |  |  |
| result | text | Yes |  | 执行结果或错误信息 |
| output_context | json | Yes |  |  |

---

### 表: `task_execution_logs`
- **描述**: 任务执行日志
- **行数**: 104
- **占用空间**: 0.38 MB (数据: 0.33MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | bigint(20) | No | PRI |  |
| task_id | varchar(100) | No | MUL | 任务ID |
| task_name | varchar(200) | No |  | 任务名称 |
| status | enum('RUNNING','SUCCESS','FAILED','TIMEOUT','CANCELLED') | No | MUL | 执行状态 |
| start_time | datetime | No | MUL | 开始时间 |
| end_time | datetime | Yes |  | 结束时间 |
| duration_seconds | int(11) | Yes |  | 执行耗时(秒) |
| exit_code | int(11) | Yes |  | 退出码 (0=成功) |
| error_message | text | Yes |  | 错误信息 |
| container_id | varchar(100) | Yes |  | Docker容器ID |
| metadata | json | Yes |  | 元数据 |
| created_at | datetime | Yes |  | 记录创建时间 |
| updated_at | datetime | Yes |  | 记录更新时间 |

---

### 表: `task_execution_stats`
- **描述**: VIEW
- **行数**: 0
- **占用空间**: 0.00 MB (数据: 0.00MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| task_id | varchar(100) | No |  | 任务ID |
| task_name | varchar(200) | No |  | 任务名称 |
| total_executions | bigint(21) | No |  |  |
| successful | decimal(23,0) | Yes |  |  |
| failed | decimal(23,0) | Yes |  |  |
| success_rate | decimal(29,2) | Yes |  |  |
| avg_duration_seconds | decimal(14,4) | Yes |  |  |
| last_run_time | datetime | Yes |  | 开始时间 |

---

### 表: `trade_cal`
- **描述**: 无备注
- **行数**: 12,720
- **占用空间**: 0.47 MB (数据: 0.47MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| cal_date | date | No | PRI | 日历日期 |
| exchange | varchar(50) | No |  | 交易所名称 (SSE 上交所, SZSE 深交所) |
| is_open | int(11) | No |  | 是否交易的标志 (0 休市, 1 交易) |
| pretrade_date | date | Yes |  | 上一个交易日的日期 |

---

### 表: `trade_date_list_for_init`
- **描述**: 空表
- **行数**: 7,472
- **占用空间**: 0.25 MB (数据: 0.25MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | Yes |  |  |

---

### 表: `ts_concept_detail`
- **描述**: 无备注
- **行数**: 0
- **占用空间**: 0.05 MB (数据: 0.02MB, 索引: 0.03MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | int(11) | No | PRI |  |
| concept_name | varchar(255) | No |  |  |
| ts_code | varchar(20) | No | MUL |  |
| name | varchar(255) | No |  |  |
| in_date | date | Yes |  |  |
| out_date | date | Yes |  |  |

---

### 表: `view_market_daily_review`
- **描述**: VIEW
- **行数**: 0
- **占用空间**: 0.00 MB (数据: 0.00MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| trade_date | date | No |  | 交易日期 |
| vol_ma_divergence | decimal(10,4) | Yes |  | VOL-01 成交额均线背离(动能差) |
| vol_rank | decimal(6,4) | Yes |  |  |
| vol_ma5_rank | decimal(6,4) | Yes |  |  |
| vol_ma20_rank | decimal(6,4) | Yes |  |  |
| vol_01_state | varchar(20) | Yes |  |  |
| margin_velocity | decimal(10,4) | Yes |  | VOL-02 融资买入动量的占比加速度 |
| congestion_velocity | decimal(10,4) | Yes |  | VOL-03 极值拥挤度的加速度(前10%虹吸比) |
| zombie_stock_derivation | decimal(10,4) | Yes |  | VOL-04 极寒无流动性股衍生率(Z-Score) |
| cost_pulse_fdr007 | decimal(10,4) | Yes |  | VOL-05 资金成本的异常脉冲(FR007) |
| non_bank_premium | decimal(10,4) | Yes |  | VOL-05 辅助非银流动性溢价(R007-FR007) |
| etf_depletion_rate | decimal(10,4) | Yes |  | VOL-06 ETF被动护盘的效用消耗斜率 |

---

### 表: `wencai_fund_holdings`
- **描述**: 无备注
- **行数**: 24,990
- **占用空间**: 3.52 MB (数据: 3.52MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI | TS代码 |
| name | varchar(100) | Yes |  | 股票名称 |
| end_date | date | No | PRI | 截止日期 |
| hoding_counts | int(11) | Yes |  | 持股家数 |
| mkv | float | Yes |  | 持有股票市值(元) |
| holding_amount | float | Yes |  | 截止日期持有股票数量（股） |
| stk_float_ratio | float | Yes |  | 占流通股本比例 |

---

### 表: `wencai_stock_industry`
- **描述**: 无备注
- **行数**: 5,248
- **占用空间**: 1.52 MB (数据: 1.52MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI | TS代码 |
| name | varchar(100) | No |  | 指数简称 |
| level1 | varchar(100) | No |  | 一级行业 |
| level2 | varchar(100) | No |  | 二级行业 |
| level3 | varchar(100) | No |  | 三级行业 |

---

### 表: `wencai_zd_concept_industry`
- **描述**: 无备注
- **行数**: 717
- **占用空间**: 0.08 MB (数据: 0.08MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| ts_code | varchar(20) | No | PRI | TS代码 |
| name | varchar(100) | No |  | 指数简称 |
| type | varchar(100) | No |  | 行业(概念)类型 |
| level | varchar(50) | Yes |  | 行业级别 |

---

### 表: `workflow_definitions`
- **描述**: Workflow definition templates
- **行数**: 6
- **占用空间**: 0.02 MB (数据: 0.02MB, 索引: 0.00MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| id | varchar(100) | No | PRI |  |
| name | varchar(255) | No |  |  |
| version | int(11) | Yes |  |  |
| definition | json | No |  | The DAG definition in JSON/YAML format |
| created_at | datetime | Yes |  |  |
| updated_at | datetime | Yes |  |  |

---

### 表: `workflow_runs`
- **描述**: Workflow instance execution tracking
- **行数**: 237
- **占用空间**: 4.34 MB (数据: 4.30MB, 索引: 0.05MB)

| 字段名 | 类型 | 必填 | 键 | 备注 |
|---|---|---|---|---|
| run_id | char(36) | No | PRI |  |
| workflow_id | varchar(100) | No | MUL |  |
| status | enum('PENDING','RUNNING','COMPLETED','FAILED','CANCELLED') | Yes |  |  |
| context | json | Yes |  | Global runtime context |
| start_time | datetime | Yes |  |  |
| end_time | datetime | Yes |  |  |

---
