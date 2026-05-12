# E300-S1 技术报告: ODS 层字段对齐与 Mapping 矩阵认证

## 1. 验证概述
审计时间: 2026-05-12 21:56:36.781247
审计表总数: 24

## 2. 审计结果矩阵

| 表名 | 接口名 | DB 字段数 | API 字段数 | 状态 | 缺失字段 (API有/DB无) |
|---|---|---|---|---|---|
| stock_basic_info | stock_basic | 19 | 10 | PASS | - |
| trade_cal | trade_cal | 4 | 4 | PASS | - |
| stock_kline_daily | daily | 13 | 11 | WARN | change, vol |
| ods_index_daily | index_daily | 14 | 0 | PASS | - |
| daily_basic | daily_basic | 18 | 18 | PASS | - |
| ods_event_limit_pool | limit_list | 20 | 14 | WARN | amp, fc_ratio, fl_ratio, fd_amount, first_time, last_time, strth, limit |
| ods_sw_index_daily | index_dailysw | 17 | 0 | PASS | - |
| stock_balance_sheet | balancesheet | 21 | 0 | PASS | - |
| stock_income_statement | income | 21 | 0 | PASS | - |
| stock_cash_flow_statement | cashflow | 12 | 0 | PASS | - |
| stock_finance_indicators | fina_indicator | 12 | 0 | PASS | - |
| stock_shareholder_count | stk_holdernumber | 7 | 4 | WARN | ann_date, holder_num |
| stock_top10_shareholders | top10_holders | 10 | 9 | WARN | ann_date, hold_amount, hold_ratio, hold_float_ratio, hold_change, holder_type |
| stock_north_funds_daily | moneyflow_hsgt | 7 | 7 | WARN | ggt_ss, ggt_sz, hgt, sgt, north_money, south_money |
| stock_lhb_daily | top_list | 17 | 15 | WARN | name, close, pct_change, amount, l_sell, l_buy, l_amount, net_amount, net_rate, amount_rate, float_values |
| stock_block_trade | block_trade | 9 | 7 | WARN | vol |
| ods_holdertrade | - | - | - | FAIL | - |
| ods_repurchase | - | - | - | FAIL | - |
| ods_dividend | - | - | - | FAIL | - |
| ods_investigation | - | - | - | FAIL | - |
| ods_forecast | - | - | - | FAIL | - |
| ods_express | - | - | - | FAIL | - |
| ods_share_release | - | - | - | FAIL | - |
| ods_index_global_daily | - | - | - | FAIL | - |

## 3. 核心发现与风险提示

> [!IMPORTANT]
> 本报告仅作标注，未对数据库执行任何修改。

### 待关注差异项
- **stock_kline_daily**: 字段不匹配
- **ods_event_limit_pool**: 字段不匹配
- **stock_shareholder_count**: 字段不匹配
- **stock_top10_shareholders**: 字段不匹配
- **stock_north_funds_daily**: 字段不匹配
- **stock_lhb_daily**: 字段不匹配
- **stock_block_trade**: 字段不匹配
- **ods_holdertrade**: Table not found in DB
- **ods_repurchase**: Table not found in DB
- **ods_dividend**: Table not found in DB
- **ods_investigation**: Table not found in DB
- **ods_forecast**: Table not found in DB
- **ods_express**: Table not found in DB
- **ods_share_release**: Table not found in DB
- **ods_index_global_daily**: Table not found in DB
