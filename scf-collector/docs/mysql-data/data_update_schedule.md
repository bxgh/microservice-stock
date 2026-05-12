# 数据原始采集计划手册 v0.2

> **版本说明**：本版基于 v0.1 文档补全。v0.1 覆盖约 30% 的原始数据采集任务，本版补齐 L3 资金流 / L6 公告 / L7 跨市场三章及调度元数据机制，并修正时序冲突。
> **本手册定位**：定义 `ods_*` / `dim_*` / `meta_*` 三类原始数据的采集频率、时机、上游、关键约束。计算层（`ads_*` / `app_*`）由后续手册覆盖，不在本版范围。

---

## 背景

v0.1 文档存在以下结构性问题：

1. **覆盖度不足**：仅列出 8 张 ods_* 表，对照 `TABLES_INDEX.md` 仍缺约 15 张
2. **时序冲突**：`daily_basic` 20:00 采集与 `PROJECT_OVERVIEW` 第 4 节锁定的「17:00 L1-L4 ETL 完成」相冲突
3. **数据契约缺失**：未引入异动管线 v1.1 的 `data_readiness` 写入机制
4. **单源风险**：每个任务仅标一个上游，未声明备用源
5. **命名混用**：legacy 表名（`stock_kline_daily`）与标准前缀（`ods_*`）混用无标注

---

## 目标

- 覆盖 `PROJECT_OVERVIEW` 第 1-7 章涉及的全部原始数据表
- 时机严格对齐第 4 节锁定的盘后流水线
- 引入 `data_readiness` 数据就绪契约 + 多源备份策略 + 阻塞影响分级
- 跨期 / 长假特殊处理在表备注中显式声明

---

## 范围

| 包含 | 不包含 |
|---|---|
| `ods_*` 原始数据采集 | `ads_*` / `app_*` 计算层 |
| `dim_*` 维度表同步 | 计算指标的 ETL 设计 |
| `meta_*` 系统元数据 | 第 8 章训练系统数据采集（用户产生数据） |
| Tushare / akshare / 长桥 API 接入 | 第 9 章观察点系统采集逻辑 |
| 数据就绪契约写入机制 | 跨网同步链路（v1.1 E4 单独文档） |

## 非目标

- 不覆盖具体 ETL 代码实现
- 不定义采集失败的重试策略细节（仅声明分级）
- 不写跨网同步链路设计（属异动管线 v1.1 E4）
- 不规划计算层 ads_* / app_* 的产出时机

---

## 设计原则

### P1. 命名规范

| 类别 | 命名约定 | 处置 |
|---|---|---|
| 新建表 | `ods_*` / `dim_*` / `meta_*` 前缀 | 强制 |
| Legacy 在用表 | `stock_*` / `daily_*` 等 | 保留，本版不迁移；表格中以「(legacy)」标注 |
| Legacy 计划迁移表 | 见 `TABLES_INDEX.md` 第 8 节 | 各章首次落地时一并迁移 |

### P2. 时序对齐

所有采集任务时点严格满足 `PROJECT_OVERVIEW` 第 4 节锁定的盘后流水线：

```
15:00  收盘
16:30  Tushare / akshare 增量数据基本就绪（采集启动死线下限）
17:00  L1-L4 ETL 完成 → 行情类采集必须 17:00 前结束
17:15  L6-L8 ETL 完成 → 公告 / 资金类采集允许 17:15 前结束
17:30  综合输出完成
20:30  异动管线 v1.1 数据就绪契约满足
21:00  异动结果产出（死线 22:00）
```

任何采集任务时机违反上述链路均视为设计缺陷。

### P3. 数据就绪契约（强制）

**每个 ods 采集任务结束后必须写入 `data_readiness` 表一行**：

```sql
INSERT INTO data_readiness (data_source, trade_date, ready_at, status, row_count)
VALUES (:source_key, :trade_date, NOW(), 'ready', :row_count);
```

下游 ETL 通过订阅契约启动，不允许通过「估算时间」或「轮询表行数」的方式判断就绪。

### P4. 多源备份

| 风险等级 | 含义 | 处置要求 |
|---|---|---|
| 单源 P0 | 失败直接阻塞 L1 / L8 全链路 | 必须配备用源 |
| 单源 P1 | 失败影响单一章节 | 备用源可异步建设 |
| 单源 P2 | 失败仅影响综述质量 | 接受单源 |

### P5. 跨期 / 长假处理

以下场景必须在调度配置中预留 hook（具体实现见各章节备注）：

- ST 状态变更：长假后第一日采集前，先做全表 `name LIKE '%ST%'` 对照
- 龙虎榜：跨期累积口径，长假后第一日采集时拉前 N 个交易日
- 北向资金：2024-08-19 后口径变更，跨该日期的回算不可比

### P6. 失败告警分级

| 阻塞等级 | 告警级别 | 响应时效 | 触发条件 |
|---|---|---|---|
| P0 | CRITICAL | 立即电话 / 邮件 | 阻塞 L1 / L5 / L8 全链路 |
| P1 | ERROR | 邮件 | 阻塞单章节 |
| P2 | WARN | 日报汇总 | 仅影响综述生成 |

与异动管线 v1.1 E6 邮件告警保持一致。

---

## 1. 系统元数据 (meta_*)

| 任务名称 | 关联表 | 更新频率 | 触发时机 | 上游 | 备注 |
|---|---|---|---|---|---|
| 股票列表同步 | `stock_basic_info` (legacy → `dim_stock_basic`) | 每日 | 06:00 | Tushare | 含上市状态变更、退市标记 |
| 交易日历同步 | `trade_cal` (legacy → `meta_trading_calendar`) | 每月 | 1 号 06:30 | Tushare | 上市 ≥ 60 个交易日判定依赖此表 |
| 数据就绪契约 | `data_readiness` (→ `meta_data_readiness`) | T+0 实时 | 各 ods 任务完成时 | 各采集任务 | 异动管线 v1.1 E2 核心，详见 P3 |
| 任务编排状态 | `pipeline_run` (→ `meta_pipeline_run`) | T+0 实时 | 各 pipeline 启停时 | APScheduler | 异动管线 v1.1 E3 核心 |

---

## 2. 交易行情数据

| 任务名称 | 关联表 | 频率 | 时机 | 上游（主 / 备） | 备注 |
|---|---|---|---|---|---|
| 个股日线 | `stock_kline_daily` (legacy) | 交易日 | 16:30 | Tushare / akshare | 1200 万+ 记录，T+0 增量；前复权数据 |
| 指数日线 | `ods_index_daily` | 交易日 | 16:30 | Tushare / 长桥 | 10 个核心宽基 + 万得全 A 用 `985.SH` 替代 |
| 每日指标 | `daily_basic` (legacy) | 交易日 | **16:45** ⚠️ | Tushare | **含 PE/PB/市值，L1 计算依赖；v0.1 标 20:00 与 17:00 ETL 冲突，已修正** |
| 涨跌停池 | `ods_event_limit_pool` | 交易日 | **16:30** ⚠️ | Tushare | **v0.1 标 16:00 早于上游就绪时间，已修正**；含 `pool_type ∈ {zt, dt, zb, lian}`、`board_height`、`seal_money` |
| 申万行业行情 | `ods_sw_index_daily` | 交易日 | **16:45** ⚠️ | Tushare | 申万 l1 + l2，~530 行；**v0.1 标 17:00 留给 L2 计算时间过短** |
| 概念板块行情 | `ods_concept_kline_daily` | 交易日 | **16:50** ⚠️ | akshare / 同花顺 | 反爬限速 ≥ 1s；同名多版本（机器人 / 人形机器人）需消歧；半数 < 10 只无统计意义 |
| 市场广度 | `ods_market_breadth_daily` | 交易日 | 16:55 | Tushare 计算 | 涨跌家数 / 涨停 / 跌停 / 炸板数 |

### 时序冲突修正说明

v0.1 文档中以下三处时机与 `PROJECT_OVERVIEW` 第 4 节冲突，本版修正：

| 字段 | v0.1 | v0.2 | 修正理由 |
|---|---|---|---|
| `daily_basic` | 20:00 | 16:45 | L1 计算 17:00 启动，必须前置 |
| `ods_event_limit_pool` | 16:00 | 16:30 | Tushare 通常 16:30 才完整就绪 |
| `ods_sw_index_daily` | 17:00 | 16:45 | L2 计算 17:20 启动，留 35 min 缓冲 |

---

## 3. 财务与基本面 (Financial Data)

| 任务名称 | 关联表 | 频率 | 触发方式 | 上游 | 备注 |
|---|---|---|---|---|---|
| 资产负债表 | `stock_balance_sheet` (legacy) | 季度 | 增量扫描 `f_ann_date` | Tushare | 4/8/10 月高峰；retry 窗口 +7 天 |
| 利润表 | `stock_income_statement` (legacy) | 季度 | 同上 | Tushare | 同上 |
| 现金流量表 | `stock_cash_flow_statement` (legacy) | 季度 | 同上 | Tushare | 同上 |
| 财务指标 | `stock_finance_indicators` (legacy) | 季度 | 报表入库后触发 | Tushare | ROE / 毛利 / EPS 等 |
| 股东人数 | `stock_shareholder_count` (legacy) | 每月 | 15 号 / 月底 21:00 | Tushare | — |
| 前十大股东 | `stock_top10_shareholders` (legacy) | 每月 | 同上 | Tushare | 流通股东表单独同步（TBD：是否合并） |

> ⚠️ Tushare 财报数据 `f_ann_date`（实际公告日）和 `ann_date`（计划公告日）字段语义不同，采集逻辑以 `f_ann_date` 为准。

---

## 4. 情绪 / 估值底层指标

| 任务名称 | 关联表 | 频率 | 时机 | 上游 | 备注 |
|---|---|---|---|---|---|
| 监控指标历史 | `monitor_indicators_history` | 交易日 | 17:00 | Tushare | 含 ERP / 国债收益率；**`yield_pct` 入库一律小数（采集层 `/100`）**；`cn_gov_yield` 接口名 TBD 已确认（具体接口名待 Gemini 反馈填入）|

---

## 5. 资金五维（v0.1 完全缺失）⭐

### 5.1 北向资金

| 任务名称 | 关联表 | 频率 | 时机 | 上游（主 / 备） | 备注 |
|---|---|---|---|---|---|
| 北向资金日终 | `stock_north_funds_daily` | 交易日 | 17:00 | Tushare / 港交所 | **2024-08-19 后口径变更**：仅日终成交净额，无个股盘中；个股北向已不可用 |
| 沪深港通汇总 | `north_capital_daily` | 交易日 | 17:00 | Tushare | TBD：与上表口径区别 / 是否合并 |

### 5.2 龙虎榜

| 任务名称 | 关联表 | 频率 | 时机 | 上游（主 / 备） | 备注 |
|---|---|---|---|---|---|
| 龙虎榜营业部明细 | `stock_lhb_daily` | 交易日 | **17:30** | Tushare / akshare | akshare **必须串行 + 间隔 ≥ 1s**（反爬）；关联 `dim_yz_seat`；上市日有时滞 |
| 龙虎榜个股明细 | `stock_lhb_stock` (TBD 表名) | 交易日 | 17:30 | Tushare | 上龙虎榜个股净买入 |

### 5.3 大宗交易

| 任务名称 | 关联表 | 频率 | 时机 | 上游 | 备注 |
|---|---|---|---|---|---|
| 大宗交易 | `stock_block_trade` | 交易日 | 18:00 | Tushare | `discount_pct` **入库一律小数**；同一标的同日多笔以 `sn` 区分 |

### 5.4 融资融券

| 任务名称 | 关联表 | 频率 | 时机 | 上游 | 备注 |
|---|---|---|---|---|---|
| 两融余额（市场级） | `ods_margin_total` (TBD 表名) | 交易日 | T+1 09:00 | Tushare | T+1 数据，**当日采不到** |
| 两融个股明细 | `ods_margin_detail` (TBD 表名) | 交易日 | T+1 09:00 | Tushare | 同上 |

### 5.5 ETF 申赎

| 任务名称 | 关联表 | 频率 | 时机 | 上游（主 / 备） | 备注 |
|---|---|---|---|---|---|
| ETF 申赎 | `ods_etf_share_chg` (TBD 表名) | 交易日 | 19:00 | Tushare / akshare | **单位陷阱：share_chg 单位「亿份」**，净申购 = `share_chg × nav × 1e8`（元）；采集层不做单位转换，保留原始单位，转换在 ETL 层 |

### 5.6 游资席位维表

| 任务名称 | 关联表 | 频率 | 触发 | 上游 | 备注 |
|---|---|---|---|---|---|
| 游资席位库 | `dim_yz_seat` | 不定期 | 手工录入 | 人工 | 首批 50-100 席位录入中；`aliases` JSON 字段；**别名命中率目标 > 90%** |

---

## 6. 公告事件（v0.1 完全缺失）⭐

| 任务名称 | 关联表 | 频率 | 时机 | 上游 | 备注 |
|---|---|---|---|---|---|
| 增减持公告 | `ods_holdertrade` | 交易日 | 18:00 | Tushare | **`change_ratio` 单位陷阱**：上游有时百分比有时小数，采集层统一 `/100` |
| 回购公告 | `ods_repurchase` | 交易日 | 18:00 | Tushare | 主键含 `sn`，同公司多笔区分 |
| 分红方案 | `ods_dividend` | 交易日 | 18:00 | Tushare | 含 `ex_date` / `record_date`；除权除息日为重要事件 |
| ST 状态变更 | `ods_st_change` | 交易日 | 18:00 | Tushare 计算 | **跨周末 / 长假处理**：长假后第一日先做 `name LIKE '%ST%'` 全表对照再差分 |
| 立案调查 | `ods_investigation` | 交易日 | 18:00 | Tushare | 含 `authority` 字段；P1 风险事件 |
| 业绩预告 | `ods_forecast` (TBD 表名) | 交易日 | 18:30 | Tushare | 财报季高峰（1/4/7/10 月）；第 9 章事件日历依赖 |
| 业绩快报 | `ods_express` (TBD 表名) | 交易日 | 18:30 | Tushare | 同上 |
| 限售解禁 | `ods_share_release` (TBD 表名) | 每周 | 周五 19:00 | Tushare | 解禁日历，前瞻 30/60/90 天窗口 |
| 公告主表 | `ods_announcement` (TBD 是否单独建) | 交易日 | 18:00 | Tushare | 用于第 9 章事件日历兜底；停复牌 / 风险警示 / 重大事项 |

---

## 7. 跨市场指数（v0.1 完全缺失）

| 任务名称 | 关联表 | 频率 | 时机 | 上游（主 / 备） | 备注 |
|---|---|---|---|---|---|
| 海外指数日线 | `ods_index_global_daily` | 交易日 | **T+1 09:00** | 长桥 / Tushare | HSI / HSTECH / IXIC / SPX / DJI / VIX；**因时差 T+1 采集**，A 股盘前用前夜数据 |
| 海外指数维表 | `dim_index_global` | 静态 | 初始化一次 | 人工 | 6 个海外指数维度信息（指数名 / 市场 / 时区） |

---

## 8. 阻塞影响矩阵（P0/P1/P2 分级）

> 用于决定告警分级、重试次数、降级策略。

### P0（CRITICAL，阻塞全链路）

| 表 | 缺失影响 | 主源失败处置 |
|---|---|---|
| `stock_kline_daily` | L1 / L2 / L5 / L8 全瘫 | 切 akshare 主源；T+0 22:00 前补完 |
| `daily_basic` | L1 / L5 / L8 全瘫 | 单源风险 P0；**重试 5 次后人工介入** |
| `ods_event_limit_pool` | L1 / L3 / L8 瘫 | 切 akshare；akshare 限速注意 |
| `ods_index_daily` | L1 / L7 瘫 | 切长桥指数源 |
| `trade_cal` | 全链路装饰器失效 | 月任务，T+0 不影响；缺失立即报警 |

### P1（ERROR，阻塞单章节）

| 表 | 缺失影响 |
|---|---|
| `monitor_indicators_history` | L4 情绪 ERP 缺失 |
| `stock_north_funds_daily` | L3 北向缺失 |
| `stock_lhb_daily` | L3 龙虎榜 + L8 游资识别 |
| `ods_sw_index_daily` | L2 行业全瘫 |
| `ods_concept_kline_daily` | L2 概念部分 |
| `ods_holdertrade` / `ods_repurchase` / `ods_dividend` | L6 公告部分缺失 |
| `dim_yz_seat` | L8 游资标签精度下降 |

### P2（WARN，仅影响综述质量）

| 表 | 缺失影响 |
|---|---|
| `ods_index_global_daily` | L7 跨市场 + 综述质量 |
| `stock_block_trade` | L3 大宗交易维度缺失 |
| `ods_investigation` / `ods_forecast` / `ods_express` | L6 事件日历局部 |
| `ods_share_release` | L9 解禁前瞻 |

---

## 9. 调度时序总图

```
06:00 ── stock_basic_info (legacy → dim_stock_basic)
06:30 ── trade_cal 月任务
09:00 ── ods_index_global_daily（前夜海外指数 T+1）
       └ ods_margin_total / ods_margin_detail（两融 T+1）
─── 15:00 收盘 ───
16:30 ── stock_kline_daily / ods_index_daily / ods_event_limit_pool
16:45 ── daily_basic / ods_sw_index_daily
16:50 ── ods_concept_kline_daily (akshare 限速)
16:55 ── ods_market_breadth_daily
17:00 ── monitor_indicators_history / stock_north_funds_daily / north_capital_daily
       │  ↑ 写 data_readiness
       └─→ L1-L4 ETL 启动（17:00-17:15）
17:30 ── stock_lhb_daily（akshare 限速串行）
       │
       └─→ L6-L8 ETL 启动（17:15-17:30，分批）
18:00 ── stock_block_trade / ods_holdertrade / ods_repurchase / ods_dividend
       └ ods_st_change / ods_investigation / ods_announcement
18:30 ── ods_forecast / ods_express
19:00 ── ods_etf_share_chg
21:00 ── 月底 / 15 号：stock_shareholder_count / stock_top10_shareholders
─── 22:00 数据采集死线 ───
       │
       └─→ 异动管线 v1.1：20:30 数据就绪 → 21:00 异动结果产出
```

---

## 10. 调度建议（替换 v0.1 第 5 节）

### 10.1 双触发策略
- **首采**：按上表标定时机触发
- **校验补漏**：T+0 22:00 检查 `data_readiness` 表，对未就绪的 P0/P1 任务发起重试

### 10.2 重试策略

| 阻塞等级 | 重试次数 | 间隔 | 失败后处置 |
|---|---|---|---|
| P0 | 5 | 指数退避 1/2/4/8/16 min | CRITICAL 告警，人工介入 |
| P1 | 3 | 5 min 固定 | ERROR 告警，T+1 补 |
| P2 | 2 | 10 min 固定 | WARN 告警，可跳过 |

### 10.3 限速控制

| 数据源 | 限速规则 |
|---|---|
| Tushare | 按账户积分级别，2000 积分约 500 次/分钟 |
| akshare | 龙虎榜 / ETF / 概念接口：**串行 + 间隔 ≥ 1s** |
| 长桥 API | 见长桥文档，TBD 实测限速 |

### 10.4 跨期 / 长假 hook

- 长假后第一日 06:00 任务前：先跑 `ST 状态全表对照` 子任务
- 北向资金跨 2024-08-19 的回算：拒绝执行，提示口径变更
- 龙虎榜跨期累积：长假后第一日采集时拉前 N 个交易日（N = 假期工作日数）

---

## 11. 待确认事项 (TBD)

| ID | 描述 | 影响 | 优先级 |
|---|---|---|---|
| TBD-1 | `cn_gov_yield` 接口名（Tushare 实测） | 第 4 节 `monitor_indicators_history` | 中 |
| TBD-2 | `stock_north_funds_daily` 与 `north_capital_daily` 口径区别 / 是否合并 | 第 5.1 节 | 中 |
| TBD-3 | 两融数据表名（`ods_margin_total` / `ods_margin_detail`） | 第 5.4 节 | 中 |
| TBD-4 | ETF 申赎表名（`ods_etf_share_chg`） | 第 5.5 节 | 中 |
| TBD-5 | 业绩预告 / 快报表名（`ods_forecast` / `ods_express`） | 第 6 节 | 中 |
| TBD-6 | 限售解禁表名（`ods_share_release`） | 第 6 节 | 中 |
| TBD-7 | 公告主表是否单独建（`ods_announcement`） | 第 6 节 | 低 |
| TBD-8 | 长桥 API 实测限速规则 | 第 10.3 节 | 低 |
| TBD-9 | 流通股东表是否与十大股东表合并 | 第 3 节 | 低 |
| TBD-10 | `data_readiness` / `pipeline_run` 从 legacy 命名迁到 `meta_*` 前缀的时点 | 第 1 节 | 低 |

---

## 变更记录

| 日期 | 版本 | 变更 | 作者 |
|---|---|---|---|
| 2026-05-? | v0.1 | 初版采集计划（覆盖 ~30% ods_* 表） | (原作者) |
| 2026-05-12 | v0.2 | 补全 L3 / L6 / L7 共 16 张表；修正 daily_basic / 涨跌停 / 行业行情时序冲突；引入 data_readiness 数据契约、多源备份策略、阻塞影响分级 (P0/P1/P2)、跨期 / 长假处理 hook；新增第 10 节限速 / 重试策略 | Claude 协助 |
