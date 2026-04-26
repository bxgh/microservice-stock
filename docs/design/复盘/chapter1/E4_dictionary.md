# 第 1 章 · 数据字典与口径 (E4)

## 第 1 章涉及表

| 表名 | 层级 | 主键 | 行数预估(5 年) | 数据源 | 更新时机 |
|---|---|---|---|---|---|
| `index_basic` | DIM | `ts_code` | 数千 | Tushare | 每周更新 |
| `ods_index_daily` | ODS | `(trade_date, ts_code)` | 数百万 | Tushare | T 日 18:00 |
| `ods_market_breadth_daily` | ODS | `trade_date` | ≈ 1200 | akshare 自建 | T 日 19:00 |
| `ods_event_limit_pool` | ODS | `(trade_date, ts_code, pool_type)` | 数十万 | akshare | T 日 16:00 |
| `ads_l1_market_overview` | ADS | `trade_date` | ≈ 1200 | 派生计算 | T 日 19:30 |

## 关键字段口径

| 字段 | 单位 | 口径说明 |
|---|---|---|
| `pct_chg`(任一表) | 小数 | `0.0123 = 1.23%`,Tushare 原口径除以 100 |
| `turnover_total` | 元 | 全 A 个股成交额合计,展示层换算为亿元 / 万亿 |
| `turnover_pctile_1y` | 0–1 | 近 250 交易日分位数,0.82 表示历史 82% 分位 |
| `up_count` 等家数 | 整数 | 全 A,**剔除 B 股 + 长期停牌(≥30 日)+ 上市 < 60 日新股** |
| `limit_up_count` | 整数 | 涨停股数,涵盖一字板,口径以 `pool_type='zt'` 数量为准 |
| `max_board_height` | 整数 | 当日最高连板,首板 = 1,N 板 = N |
| `market_breadth` | 0–1 | up_count / total_count |
| `up_down_ratio` | 数值 | up_count / down_count,> 3 偏强,< 0.33 偏弱 |

## 字段映射(Tushare → DB,供采集脚本参考)

#### `index_basic`(对应 Tushare 接口 `index_basic`)

```
Tushare 字段       → DB 字段
ts_code            → ts_code
name               → name
fullname           → fullname
market             → market
publisher          → publisher
index_type         → index_type
category           → category
base_date          → base_date
base_point         → base_point
list_date          → list_date
weight_rule        → weight_rule
desc               → description       (注意:desc 是 SQL 关键字,改名)
exp_date           → exp_date
```

#### `ods_index_daily`(对应 Tushare 接口 `index_daily`)

```
Tushare 字段       → DB 字段          → 转换说明
ts_code            → ts_code
trade_date         → trade_date       → '20260425' → '2026-04-25'
close              → close
open               → open
high               → high
low                → low
pre_close          → pre_close
change             → change
pct_chg            → pct_chg          → 除以 100(百分比 → 小数)
vol                → vol
amount             → amount
```

#### `ods_event_limit_pool`(对应 akshare 接口)

```
akshare 接口                          → pool_type
stock_zt_pool_em(涨停池)             → 'zt'
stock_zt_pool_dtgc_em(跌停池)        → 'dt'
stock_zt_pool_zbgc_em(炸板池)        → 'zb'
stock_zt_pool_previous_em(连板池)    → 'lian'

字段映射(以涨停池为例,其他池字段名略有不同,实施时验证):
代码     → ts_code         (注意补 .SH/.SZ 后缀)
名称     → name
最新价   → close
涨跌幅   → pct_chg          → 除以 100
成交额   → amount
流通市值 → circ_mv
换手率   → turnover_rate    → 除以 100
首次封板时间 → first_limit_time
最后封板时间 → last_limit_time
连板数   → board_height
封板资金 → seal_money
封板次数 → seal_count
炸板次数 → open_times
所属行业 → industry
```
