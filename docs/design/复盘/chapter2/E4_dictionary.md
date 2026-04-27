# 第 2 章 · 数据字典与口径 (E4)

## E4-S1: 核心表清单

| 表名 | 层级 | 主键 | 数据源 |
|---|---|---|---|
| `ods_sw_index_daily` | ODS | `(trade_date, ts_code)` | akshare |
| `ods_concept_kline_daily` | ODS | `(trade_date, concept_code)` | akshare |
| `dim_style_factor` | DIM | `factor_code` | 手工配置 |
| `ads_l2_industry_daily` | ADS | `(trade_date, industry_code)` | 聚合 |
| `ads_l2_concept_daily` | ADS | `(trade_date, concept_code)` | 聚合 |
| `ads_l2_style_factor` | ADS | `(trade_date, factor_code)` | 聚合 |

---

## E4-S2: 关键字段口径

| 字段 | 单位 | 计算逻辑 / 含义 |
|---|---|---|
| `internal_breadth` | 0–1 | 行业或概念内上涨股票数 / 总成分股数 |
| `pe_pctile_5y` | 0–1 | 行业 PE 在过去 5 年中的分位数(0 表示极低估) |
| `rank_diff_5d` | 整数 | 今日排名 - 5 日前排名。**负数代表排名上升(走强)** |
| `persistence_score` | 0–1 | 衡量概念的持续性,基于今日与过往榜单的重叠度 |
| `spread_today` | 小数 | 多头涨幅 - 空头涨幅 |

---

## E4-S3: 字段映射 (akshare → DB)

### `ods_sw_index_daily` (申万行业)

- `ts_code`: 原始代码补 `.SI` (如 `801010` -> `801010.SI`)
- `amount`: 统一为“元”
- `turnover_rate`: 原始值除以 100(转为小数)
- `pct_chg`: 若接口未提供,需手动计算 `(close - pre_close) / pre_close`

### `ods_concept_kline_daily` (同花顺概念)

- `concept_code`: 同花顺板块 ID (通常为 30xxxx)
- `up_count / down_count`: 若接口未提供,需通过 `stock_sector_cons_ths` 实时计算
