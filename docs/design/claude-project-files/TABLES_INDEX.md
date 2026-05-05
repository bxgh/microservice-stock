# 表清单总览(TABLES_INDEX.md)

> **本文件用途**:全表元数据索引,供 Claude / Gemini 跨章节查找表与字段的入口。
> **维护原则**:仅记录表名、主键、高频引用字段、数据频率、上游依赖、关键约束。**完整 DDL 见各仓 `migrations/`**,本文件不替代 DDL。
> **关联文档**:`PROJECT_OVERVIEW.md`(章节地图)、`IMPLEMENTATION_FEEDBACK.md`(数据状态)。

---

## 通用字段约定速查

详见 `PROJECT_OVERVIEW.md` 第 2 节。常用字段:

- `ts_code` VARCHAR(20):完整代码(如 `600519.SH`)
- `symbol` VARCHAR(10):纯数字代码
- `trade_date` DATE:交易日
- `pct_chg` DECIMAL(10,6):**全库一律小数**(0.0123 = 1.23%)
- `amount` DECIMAL(20,2):**单位元**(采集层统一)
- `created_at` / `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `is_deleted` TINYINT(1) DEFAULT 0

字符集:utf8mb4 + utf8mb4_unicode_ci + DYNAMIC

---

## 1. meta_* 系统元数据

| 表名 | 主键 | 关键字段 | 频率 | 说明 |
|---|---|---|---|---|
| trade_cal | cal_date | is_open / pretrade_date | 年初批量 | 交易日历(legacy);装饰器 + SQL 计算「上市 ≥ 60 个交易日」均依赖此表 |
| data_readiness | (data_source, trade_date) | ready_at / status / row_count | T+0 实时 | 数据就绪契约(异动管线 v1.1 E2) |
| pipeline_run | run_id | pipeline_name / start_at / end_at / status / error_msg | T+0 实时 | 任务编排状态机(异动管线 v1.1 E3) |

> ⚠️ 上述三张表当前仍使用 legacy 命名（无 `meta_` 前缀），计划在 v1.2 统一迁移。

---

## 2. dim_* 维度表

| 表名 | 主键 | 关键字段 | 频率 | 说明 |
|---|---|---|---|---|
| index_basic | ts_code | name / market / category | 月更 | 指数维表;含 10 个核心宽基;目标名 `dim_index_basic` |
| dim_style_factor | factor_code | factor_name / long_index / short_index | 静态 | 风格因子定义,4 因子(含股息/微盘等) |
| dim_anomaly_score_weight | (version, weight_key) | weight_value / is_active | 静态 | 信号评分权重配置 |
| dim_tag_dictionary | tag_code | tag_name_cn / tag_category | 静态 | 系统内置标签字典 |
| dim_yz_seat | seat_id | seat_name / aliases (JSON) | 手工录入 | 游资席位库(🚧 待开发/录入中);⚠️ 别名命中率目标 > 90% |

---

## 3. ods_* 原始数据层(按章节分组)

### 第 1 章 · L1 市场全景

| 表名 | 主键 | 关键字段 | 频率 | 上游 | 说明 |
|---|---|---|---|---|---|
| ods_index_daily | (ts_code, trade_date) | open / close / pre_close / pct_chg / amount / vol | T+0 17:00 | Tushare | 10 个核心宽基日线;万得全 A 用 `985.SH` 中证全指替代 |
| ods_event_limit_pool | (ts_code, trade_date) | pool_type / board_height / seal_money / pct_chg / amount | T+0 17:00 | Tushare | `pool_type ∈ {zt, dt, zb, lian}`;首板 `board_height = 1` |
| ods_market_breadth_daily | trade_date | up_count / down_count / limit_up_count / limit_down_count | T+0 17:00 | Tushare 计算 | 涨跌家数 |

### 第 2 章 · L2 行业风格

| 表名 | 主键 | 关键字段 | 频率 | 上游 | 说明 |
|---|---|---|---|---|---|
| ods_sw_index_daily | (ts_code, trade_date) | close / pct_chg / amount | T+0 17:00 | Tushare | 申万 l1 + l2,~530 行 |
| ods_concept_kline_daily | (concept_code, trade_date) | close / pct_chg / amount / up_count / down_count | T+0 17:10 | akshare / 同花顺 | ⚠️ 半数概念 < 10 只无统计意义,需过滤;同名多版本(机器人 / 机器人概念 / 人形机器人)需消歧 |

### 第 3 章 · L4 情绪与连板

| 表名 | 主键 | 关键字段 | 频率 | 上游 | 说明 |
|---|---|---|---|---|---|
| monitor_indicators_history | (indicator_code, trade_date) | indicator_value / yield_pct | T+0 / T+1 | Tushare | 含 ERP / 国债收益率;`yield_pct` 一律小数。**TBD:`cn_gov_yield` 接口名实测确认状态** |

### 第 4 章 · L3 资金流

| 表名 | 主键 | 关键字段 | 频率 | 上游 | 说明 |
|---|---|---|---|---|---|
| stock_north_funds_daily | trade_date | net_buy_amount / total_amount | T+0 日终 | 港交所 / Tushare | 北向**仅日终**,2024-08-19 后无个股盘中数据 |
| north_capital_daily | trade_date | hgt_net / sgt_net / total_net | T+0 日终 | Tushare | 沪深港通汇总(与上表口径区别 TBD,可能合并) |
| stock_lhb_daily | (ts_code, trade_date, seat_id) | buy_amount / sell_amount / net_amount | T+0 17:30 | Tushare | 龙虎榜营业部明细,关联 `dim_yz_seat` |
| stock_block_trade | (ts_code, trade_date, sn) | price / volume / discount_pct | T+0 18:00 | Tushare | 大宗交易;`discount_pct` 一律小数 |

### 第 6 章 · L6 公告

| 表名 | 主键 | 关键字段 | 频率 | 上游 | 说明 |
|---|---|---|---|---|---|
| ods_holdertrade | (ts_code, ann_date, holder_name, sn) | change_ratio / change_vol / direction | T+0 18:00 | Tushare | ⚠️ `change_ratio` 上游有时百分比有时小数,采集层统一 `/100` |
| ods_repurchase | (ts_code, ann_date, sn) | repurchase_amount / progress | T+0 18:00 | Tushare | 回购公告 |
| ods_dividend | (ts_code, ann_date) | cash_div_per_share / ex_date / record_date | T+0 18:00 | Tushare | 分红方案 |
| ods_st_change | (ts_code, change_date) | old_status / new_status / reason | T+0 18:00 | Tushare 计算 | ST 状态差分;⚠️ 跨周末 / 长假需先做「name 包含 ST」全表对照后再差分 |
| ods_investigation | (ts_code, ann_date) | reason / authority | T+0 18:00 | Tushare | 立案调查 |

### 第 7 章 · L7 跨市场

| 表名 | 主键 | 关键字段 | 频率 | 上游 | 说明 |
|---|---|---|---|---|---|
| ods_index_global_daily | (ts_code, trade_date) | close / pct_chg | T+1(因时差) | 长桥 / Tushare | 海外指数 6 个 |

---

## 4. ads_* 应用数据层(按表前缀,跨章查询)

| 表名 | 章节 | 主键 | 关键字段 | 频率 | 说明 |
|---|---|---|---|---|---|
| ads_l1_market_overview | 1 | trade_date | idx_sh_close / idx_sh_pct / turnover_total / up_count / market_regime | T+0 17:18 | 每日 1 行 |
| ads_l2_industry_daily | 2 | (industry_code, trade_date) | industry_name / pct_chg / internal_breadth / top_stock_code | T+0 17:20 | 31 个申万 l1;rank_5d/20d 已修复非空 |
| ads_l2_concept_daily | 2 | (concept_code, trade_date) | persistence_score / theme_label | T+0 17:20 | 概念结构指标 |
| ads_l2_style_factor | 2 | (factor_code, trade_date) | spread_today / direction | T+0 17:20 | 4 行 / 日 |
| ads_l3_capital_flow | 4 | trade_date | main_net / north_net / margin_net | T+0 17:25 | 🚧 待开发 |
| ads_l4_sentiment | 3 | trade_date | promote_rate / money_effect / erp_pctile | T+0 17:25 | 🚧 待开发 |
| ads_l8_unified_signal | 5 | (ts_code, trade_date, signal_type) | composite_score / resonance_level / explanation_zh | T+0 17:22 | 异动信号池 |
| ads_stock_derived_metrics | 5 | (ts_code, trade_date) | volume_ratio_5d / volume_ratio_20d / dist_to_ma20 / dist_to_ma250 | T+0 17:18 | 派生指标层,L8 评分上游 |

---

## 5. app_* 应用面表(前端 / 网关直查)

| 表名 | 章节 | 主键 | 关键字段 | 频率 | 说明 |
|---|---|---|---|---|---|
| app_anomaly_top10_daily | 5 | id | composite_score / quota_slot | T+0 21:00 | 异动 Top 10 推送清单 |
| app_daily_brief | 7 | trade_date | context_snapshot (JSON) | T+0 17:30 | 🚧 待开发; 结构化字段 + LLM 综述 |
| app_watchlist_next_day | 7 | (trade_date, ts_code) | watch_reason | T+0 17:34 | 🚧 待开发; 次日观察 Top 10 |

---

## 6. obs_* 观察点系统(第 9 章 · 设计已交付 / 待开发)

| 表名 | 主键 | 关键字段 | 说明 |
|---|---|---|---|
| obs_observation_point | obs_id | observed_at / trigger_event / context_snapshot (JSON) | 触发观察的时点 |
| obs_hypothesis | hypothesis_id | obs_id / hypothesis_text / verification_method | 一个观察点 N 个假设 |
| obs_target_pool | (hypothesis_id, ts_code) | weight | 多对多绑定标的 |
| obs_verification_window | (hypothesis_id, window_type) | t_plus / window_start / window_end | T+20 / T+30 验证窗口 |
| obs_verification_result | (hypothesis_id, window_type) | actual_data (JSON) / verdict / notes | `verdict ∈ {confirm, refute, partial, inconclusive}` |

---

## 7. train_* 认知训练系统(第 8 章 · 设计已锁定 / 待开发)

> 当前 legacy 表为 `diary_entry` / `diary_stock`,新开发使用 `train_*` 前缀。

| 表名 | 主键 | 关键字段 | 说明 |
|---|---|---|---|
| train_prediction_main | prediction_id | trade_date / version_tier / submitted_at | 晨间预判主表 |
| train_prediction_item | (prediction_id, field_id) | value (JSON) / validation_status | 训练项明细,关联 `dim_training_field` |
| train_journal_daily | (user_id, trade_date) | content (JSON) | 每日日记(legacy: `diary_entry`) |
| train_decision_main | decision_id | trade_date / ts_code / direction / quadrant | 决策日志主表 |
| train_decision_item | (decision_id, field_id) | value (JSON) | 决策日志明细 |
| train_weekly_review | (user_id, week_start) | content (JSON) / pattern_summary | 周末复盘 |

校验方法 `validator_method ∈ {threshold_mapping, json_intersection, manual_review, outcome_inference}`

版本档位 `version_tier ∈ {entry, intermediate, full}`,5 项 / 8 项 / 12 项,解锁条件见 PROJECT_OVERVIEW 第 5 节第 8 章。

---

## 8. legacy 表(存量,新开发禁用)

| 表名 | 章节归属 | 现状 | 迁移目标 / 处置 |
|---|---|---|---|---|
| stock_kline_daily | 多章节 | 在用 | 1200万+ 记录, 暂不迁移 |
| daily_basic | 多章节 | 在用 | 1100万+ 记录, 暂不迁移 |
| index_basic | 1 | 在用 | → `dim_index_basic` |
| trade_cal | 全部 | 在用 | → `meta_trading_calendar` |
| data_readiness | 异动管线 | 在用 | → `meta_data_readiness` |
| pipeline_run | 异动管线 | 在用 | → `meta_pipeline_run` |
| monitor_health_scores | 3 | 在用 | 情绪评分历史 |

---

## 9. 单位 / 命名陷阱速查(高频引用)

> 与 `PROJECT_OVERVIEW.md` 第 3 节互引,本节作字段级速查清单。

| 字段 / 表 | 陷阱 | 处理 |
|---|---|---|
| 全库 `pct_chg` | 上游可能为百分比 | 采集层 `/100`,入库一律小数 |
| `holdertrade.change_ratio` | 上游有时百分比有时小数 | 采集层规范化为小数 |
| ETF `share_chg` | 单位「亿份」 | 净申购 = `share_chg × nav × 1e8` |
| `yield_pct`(国债收益率) | 上游为百分比 | 采集层 `/100`,一律小数 |
| `amount`(成交额) | 上游可能是千元 / 万元 | 采集层统一为元 |
| 涨跌停阈值 | 主板 9.7% / 创业板 19.7% / ST 4.7% / 北交所 29.7% | 当前简化版 9.7%,**前端必须注明** |
| 个股北向 | 2024-08-19 后无盘中数据 | 跨期不可比,放弃个股北向 |
| `is_deleted` | 软删除字段 | 默认 0,查询必须过滤 `is_deleted = 0` |

---

## 10. TBD 字段 / Schema 清单(汇总)

> 实施侧落地后逐项销账,与 `PROJECT_OVERVIEW.md` 第 7 节对齐。

### 高优先级
- [ ] `dim_style_factor` 微盘代码字段值(影响 `dividend_vs_micro` 因子)
- [ ] `monitor_indicators_history`:`cn_gov_yield` 接口名实测确认
- [ ] `ads_l8_unified_signal.anomaly_score` 跨板块归一方案

### 中优先级
- [ ] `ads_l9_calendar_upcoming` 是否拆为 `ads_l9_calendar_market`
- [ ] `stock_north_funds_daily` 与 `north_capital_daily` 口径区别 / 是否合并
- [ ] meta_* 三表迁移时点(从 legacy 命名迁到 `meta_` 前缀)

### 低优先级 / 待 Gemini 反馈
- [ ] 异动管线 v1.1 新增表组(E5)的具体表名 / schema
- [ ] 任务状态机表(关联 `meta_pipeline_run`)的字段补全
- [ ] L8 v1.1 跨网同步表(可能新增)

---

## 11. 跨表依赖速查

> 仅列出**章节间**和**跨仓**的关键依赖。同章内依赖见各章设计文档。

```
ods_event_limit_pool ─┬─→ ads_l1_market_overview (1)
                      └─→ ads_l4_sentiment (3)
                          └─→ ads_l8_unified_signal (5)

ods_index_daily ──────→ ads_l1_market_overview (1)
                  └───→ ads_l2_style_factor (2)
                  └───→ ads_l5_valuation (7)

stock_kline_daily ────→ ads_stock_derived_metrics (5)
                  └───→ ads_l8_unified_signal (5)

dim_yz_seat ──────────→ stock_lhb_daily (4)
                  └───→ ads_l3_capital_flow (4)
                  └───→ ads_l8_unified_signal.has_yz_seat (5)

ads_l1 + l2 + l3 + l4 + l5 + l6 + l7 ──→ app_daily_brief (7)
                                    └──→ app_watchlist_next_day (7)
                                         (内网仓产出 → 双写 → 云端 wxch-gateway 读)
```

---

**变更记录**

| 日期 | 版本 | 变更 | 作者 |
|---|---|---|---|
| 2026-05-05 | v0.1 | 骨架初版,基于 PROJECT_OVERVIEW.md / IMPLEMENTATION_FEEDBACK.md 提取 | Claude 协助 |
| 2026-05-05 | v0.2 | 核对版,包括腾讯云mysql数据库和内网ck数据库