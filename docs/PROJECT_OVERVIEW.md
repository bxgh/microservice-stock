# 项目总览：A 股盘后分析系统

> **本文件用途**：作为 project knowledge 的索引层，任何关于本项目的对话先读此文件，再按需读对应章节文档。
> **维护原则**：本文件只放高频检索内容；具体设计细节在各章节 .md 文件中。

---

## 0. 项目元信息

| 项 | 值 |
|---|---|
| 项目名 | A 股盘后分析系统 |
| 定位 | 个人投资者使用的盘后数据观察 + 认知训练平台 |
| 终端 | 微信小程序（Taro / 原生）|
| 数据范围 | A 股为主，含港股 / 美股核心指数 |
| 数据频率 | T+0 盘后（17:00 后批量计算）|
| 版本 | 详见各章节文档 |

## 0.1 代码仓库

| 角色 | 仓库 / 路径 | 部署目标 |
|---|---|---|
| 数据采集 | `bxgh/microservice-stock` | 腾讯云 |
| 小程序后端 API(网关) | `bxgh/microservice-stock` 的 `wxch-gateway/` | 腾讯云(同仓部署) |
| 内网计算 + MySQL/CK 双写 | `bxgh/microservice-stock-ck`（本地目录通常为 `microservice-stock`） | 内网服务器(16C / 64G / 160G SSD) |
| 小程序前端代码 | `bxgh/microstock-taro` | 微信开放平台 |

> 主分支约定、服务器地址、SSH 配置、密钥**不录入 project knowledge**,见各仓 README / 内部运维文档。

**仓间关系**:两仓为**独立代码基线**,不存在代码同步关系,仅通过数据通道交互。

## 0.2 跨网数据流

```
[腾讯云 microservice-stock]
   采集 ods_*(Tushare / akshare / 长桥)
        │
        ▼  跨网同步(SLA < 5 min)
[内网 microservice-stock-ck]
   计算 dwd_* / ads_* / app_*
   双写 MySQL + ClickHouse
        │
        ▼  双写回流到云端 MySQL
[腾讯云 microservice-stock / wxch-gateway]
   暴露 HTTP API
        │
        ▼
[微信小程序前端]
```

调度时点见第 4 节。SLA / 死线见异动管线 v1.1(第 5 章 / 横切方案)。

## 1. 技术栈

| 层 | 选型 | 备注 |
|---|---|---|
| 关系数据库 | MySQL 5.7 | 注意 JSON 索引缺失、无窗口函数；utf8mb4 + DYNAMIC |
| 时序/分析库 | ClickHouse | 与 MySQL 双写，CK 用于历史回算 |
| 数据采集 | Tushare（2000 积分）/ akshare / 长桥 API | akshare 反爬严格需限速 |
| 调度 | APScheduler + 自研 JSON pipeline | `post_market_def.json` / `pre_market_prep_def.json` |
| 后端 | Python（FastAPI 风格异步全栈）| Pydantic v2 + JSON 日志 + request_id |
| 前端 | 微信小程序 | echarts-for-weixin |
| 实施侧协作 | Gemini / Antigravity | 设计在 Claude，实施在 Gemini |
| LLM 接入 | DeepSeek-V3 | 中文金融场景，成本可控 |

## 2. 命名与编码规范（已锁定，跨章节统一）

```
表前缀约定：
  ods_*  原始数据层（Original Data Layer，永不修改）
  dwd_*  明细层（Data Warehouse Detail，清洗/脱敏后）
  dim_*  维度表（Dimension，基础信息/字典）
  ads_*  应用数据层（Application Data Service，每日聚合/指标）
  app_*  应用面表（App Data，前端直查专用）
  obs_*  观察点系统专属（第 9 章）
  train_* 认知训练专属（第 8 章，存量迁移中，目前使用 diary_*）
  meta_*  系统元数据（trading_calendar / data_readiness / pipeline_run）

存量/兼容层（Legacy Layer）：
  stock_* / daily_* / raw_* / sys_*  早期模块表名，新开发任务严禁使用。

字段约定：
  ts_code      VARCHAR(20)  完整代码，如 600519.SH（存量表可能为 VARCHAR(10/16)）
  symbol       VARCHAR(10)  纯数字代码，如 600519
  trade_date   DATE         交易日
  pct_chg      DECIMAL(10,6) 一律存小数（0.0123 代表 1.23%）
  amount       DECIMAL(20,2) 元（注意：Tushare 等上游返回千元或万元，入库前统一转为“元”）
  created_at / updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  is_deleted   TINYINT(1) DEFAULT 0  软删除

字符集：utf8mb4 + utf8mb4_unicode_ci + DYNAMIC
DDL 规则：所有 DDL 进 migrations/ 目录，使用 Alembic 或独立 SQL 脚本管理，禁止内嵌业务代码。
```

## 3. 关键约束（编码前必读，避免踩坑）

### 数据源约束
- **北向资金 2024-08-19 起**港交所不再披露盘中实时数据，仅日终成交净额。**个股北向已无法获取，跨期不可比**。
- **akshare 反爬严格**：龙虎榜 / ETF 申赎接口需限速调用，建议串行 + 间隔 ≥ 1s
- **外部接口防护**：针对 akshare/Tushare 等三方限速与网络抖动，**必须强制实现 CircuitBreaker（熔断器）和 RetryPolicy（重试机制）**。涉及共享状态（连接池、内存字典）的修改，必须使用 `asyncio.Lock()` 保障并发安全。
- **Tushare 涨跌停板块差异**：主板 9.7% / 创业板 19.7% / 科创板 19.7% / ST 4.7% / 北交所 29.7% — 当前简化版按主板阈值，**前端必须注明**
- **akshare/同花顺概念半数 < 10 只**，无统计意义；同名概念多版本（机器人 / 机器人概念 / 人形机器人），**直接用会出大量虚假信号**

### 单位陷阱（已知踩过的坑）
- Tushare `holdertrade.change_ratio`：有时百分比有时小数 → ODS 层统一存小数，采集脚本 `/100`
- ETF `share_chg` 单位「亿份」 → 计算净申购需 `share_chg × nav × 1e8`
- 国债收益率 `yield_pct` → 一律存小数（0.0265 而非 2.65）
- 涨跌幅 `pct_chg` → 全库一律小数

### MySQL 5.7 限制
- 无窗口函数 → 用条件聚合 + 自连接替代（性能损失大，全 A × 250 日量级查询 30s+）
- 无 CHECK 约束 → 业务校验放应用层
- JSON 路径查询性能差 → 关键字段冗余到独立列
- 变量赋值依赖 ORDER BY 隐性行为 → 8.0 升级会失效，**避免依赖**

## 4. 调度时点对齐（生产现状）

```
盘后数据生产流水线（交易日）：
  15:00  收盘
  16:30  Tushare/akshare 增量数据基本就绪
  16:45  Gate-3（盘后审计 / Sync Consistency Audit）校验 MySQL↔CK 双写一致性
  17:00  L1-L4 ETL 完成（Gate-3 通过后方可执行）
  17:15  L6-L8 ETL 完成
  17:18  派生指标层（Derived Metrics）
  17:20  市场状态判定（Market State）
  17:22  三池产出与标签判定（Strong/Early/Trap）
  17:28  多维印证（Resonance/Counter/Temporal）
  17:30  综合评分 + 中文说明
  17:34  Top 10 推送生成
  17:35  前端拉取窗口开启

异动管线 v1.1 修订时点：
  20:30  数据就绪契约满足
  21:00  异动结果产出（死线 22:00）
```

## 5. 章节地图

> **状态**：✅ 已交付设计 / ⏳ 实施中 / ⚠️ 实施未反馈 / 🚧 待开发
>
> 各章状态由用户在 IMPLEMENTATION_FEEDBACK.md 中维护。

### 第 1 章 · L1 市场全景

**核心表**：`index_basic`、`ods_index_daily`、`ods_market_breadth_daily`、`ods_event_limit_pool`、`ads_l1_market_overview`

**关键产出**：
- 10 个核心宽基（含中证全指替代万得全 A）
- 涨跌停池含 `pool_type ∈ {zt, dt, zb, lian}`、`board_height`（首板=1）、`seal_money`、`open_times`
- L1 全景指标 `market_regime ∈ {broad_up, broad_down, structural, low_vol}`

**依赖**：无（基础章节）

**状态**：⚠️ 实施未反馈 [需用户确认]

### 第 2 章 · L2 行业风格

**核心表**：`ods_sw_index_daily`（含 l1/l2 申万）、`ods_concept_kline_daily`、`dim_style_factor`、`ads_l2_industry_daily`、`ads_l2_concept_daily`、`ads_l2_style_factor`

**4 个风格因子**：`large_vs_small` / `value_vs_growth` / `dividend_vs_micro` / `north_vs_south`
- 微盘代码 TBD（万得微盘股代码待确认，缺失时 fallback 到 3 因子）

**主题标签枚举**：`main_theme` / `follow_up` / `one_day` / `declining`
**热度标签**：`hot` / `warm` / `normal` / `cold`

**已知问题**（已修复）：原实施漏跑 5/20 日排名 UPDATE 步骤，导致 `rank_5d` / `rank_20d` 全空。修复方案见对话历史 04-27。

**依赖**：第 1 章

**状态**：⏳ 实施中（已修复 6 项偏差）

### 第 3 章 · L4 情绪与连板

**核心表**：`monitor_indicators_history`（含 ERP/国债收益率指标）、`ads_l4_sentiment`（每日 1 行）

**关键指标**：连板梯队（首/二/三/N 板）、晋级率、炸板率、赚钱效应、ERP（10 年分位数）、异象票（一字 / 天地板 / 地天板）

**依赖**：第 1 章 `ods_event_limit_pool`、`stock_kline_daily`、`daily_basic`

**状态**：⚠️ 实施未反馈

### 第 4 章 · L3 资金流

**核心表**：`stock_north_funds_daily`、`north_capital_daily`、`stock_lhb_daily`、`stock_block_trade`、`dim_yz_seat`、`ads_l3_capital_flow`

**资金五维**：主力 / 北向（仅日度）/ 两融 / ETF 申赎 / 龙虎榜（含游资席位识别）

**首批 dim_yz_seat 50-100 席位需手工录入**，别名命中率目标 > 90%

**依赖**：第 1 章、第 3 章

**状态**：⚠️ 实施未反馈

### 第 5 章 · L8 个股异动池

**核心表**：`ads_l8_unified_signal`、`ads_stock_derived_metrics`、（v1.1 新增异动管线表组）

**6 类异动**：`top_gainer` / `top_loser` / `high_turnover` / `volume_spike` / `breakout` / `lhb`
**辅助标签**：`has_yz_seat` / `is_one_word` / `is_t_shape` / `has_event_today`

**评分公式**：`anomaly_score = 0.3 × score_pct_chg + 0.3 × score_volume + 0.2 × score_event + 0.2 × score_position`
- ⚠️ 已知问题：评分分布偏态，Top 50 集中在 90+，跨板块归一未做（涨停板块差异未消除）
- ⚠️ 权重 0.3/0.3/0.2/0.2 缺乏理论依据，需要回测校准

**样本剔除**：ST、上市 < 60 个交易日（按 trade_cal 算）、停牌、B 股

**依赖**：第 1-4 章

**状态**：⏳ 实施中（v1.1 部署方案已交付，2026-05-03）

### 第 6 章 · L6 公告 + L9 事件日历

**核心表**：`ods_holdertrade`、`ods_repurchase`、`ods_dividend`、`ods_st_change`、`ods_investigation`、`ads_l6_event_daily`、`ads_l9_calendar_upcoming`

**事件类型**：增减持 / 回购 / 分红 / ST 状态变更 / 立案调查 / 业绩披露窗口（市场级）/ 解禁

**ST 状态差分**：跨周末/长假需先做"name 包含 ST" 全表对照后再差分

**依赖**：第 1-5 章

**状态**：⚠️ 实施未反馈

### 第 7 章 · L5 估值 + L7 跨市场 + L9 综述 APP

**核心表**：`ods_index_global_daily`（HSI/HSTECH/IXIC/SPX/DJI/VIX）、`dim_index_global`、`ads_l5_valuation`、`ads_l7_cross_market`、`app_daily_brief`、`app_watchlist_next_day`

**估值口径**：宽基 / 行业 PE-TTM / PB / 股息率近 10 年分位数（周更）

**`app_daily_brief`**：每日综述结构化字段（context_snapshot），文本生成由前端调 LLM，本章只产结构化数据

**依赖**：第 1-6 章

**状态**：⚠️ 实施未反馈

### 第 8 章 · 认知训练系统

**架构哲学**：元数据驱动 + 训练项可热扩展

**核心表**：
- `dim_training_field`（元数据，配置驱动）
- `train_prediction_main` / `train_prediction_item`（目标表名，目前 legacy 为 `diary_entry` / `diary_stock` 兼容）
- `train_journal_daily`（目标表名，目前 legacy 为 `diary_entry`）
- `train_decision_main` + `train_decision_item`（决策日志）
- `train_weekly_review`（周末复盘）

**4 个训练动作**：晨间预判 / 每日日记 / 决策日志 / 周末复盘
**3 个版本档位**：entry(5 项) / intermediate(8 项) / full(12 项)
- entry → intermediate：连续 30 个交易日填满解锁
- intermediate → full：连续 60 个交易日填满解锁

**校验方法**：`threshold_mapping` / `json_intersection` / `manual_review` / `outcome_inference`

**关键风险**（已记录但未销账）：
- `theme_stage_check` 主观性强，初版 manual_review，3 个月后规则化
- `lucky_win` T+20 误伤需手动 override（月报 1 次配额）
- 冷启动 30 天显示"训练日记本"模式，不出准确率

**依赖**：第 7 章 `app_daily_brief`（context_snapshot 来源）

**状态**：✅ 设计已交付（终版） / 🚧 待开发

- **跨仓字段契约**:
  - `ods_*` 表结构由云端仓 `microservice-stock` 定义,内网仓 `microservice-stock-ck` 消费
  - `ads_*` / `app_*` 表由内网仓产出,云端 `wxch-gateway` 消费
  - 任一仓修改跨仓表 schema(字段增删 / 类型变更 / 单位变更),必须在 `IMPLEMENTATION_FEEDBACK.md` 标注「跨仓 schema 变更:仓 A → 仓 B」并通知对侧
  - 字段命名 / 单位规范见第 2 节,跨仓不允许各自约定

### 第 9 章 · 行情追溯与假设验证（观察点系统）

**核心表**：`obs_observation_point`、`obs_hypothesis`、`obs_target_pool`（多对多绑定）、`obs_verification_window`、`obs_verification_result`

**核心命题**：把交易直觉转化为可验证的假设，T+20 / T+30 数据校准市场认知

**典型场景**：寒武纪涨停 → 假设 A（虹吸）vs 假设 B（带动板块）→ 20 日后用资金/涨跌幅/超额收益数据验证

**依赖**：第 1-8 章（特别是 L8 异动池）

**状态**：✅ 设计已交付 / 🚧 待开发

### 横切：异动管线 v1.1 部署方案（2026-05-03）

**11 个 Epic、35 个 Story**，覆盖：
- E1 CalendarService + 交易日装饰器
- E2 数据就绪契约
- E3 任务状态机 + 编排
- E4 跨网数据同步（云端采集 + 内网计算 + 双写）
- E5 异动管线（8 个 task，20:30 → 21:00 时间线）
- E6 邮件告警分级（WARN/ERROR/CRITICAL）
- E7 部署运维（docker-compose + SSH 隧道 + 内网 MySQL）
- E8 实施路径（5 阶段 / 14 工作日 / 5-6 周）
- E9-E11 技术依赖 / 风险矩阵 / 度量 SLA

**关键 SLA**：异动管线 21:00 前完成、跨网同步 < 5 min、双写一致性 100%

**关联**：CCI Monitor 是另一个独立项目，不属于本盘后体系

## 6. 跨章节关键决策日志

| 决策 | 日期 | 影响章节 | 内容 |
|---|---|---|---|
| 全库 pct_chg 一律小数 | - | 全部 | 采集层统一 /100 |
| 涨停阈值简化版 9.7% | - | 第 1/3/5 章 | 前端必须注明，不消除板块差异 |
| 北向只用日度 | 2024-08 后 | 第 4 章 | 个股北向放弃，跨期不可比 |
| 万得全 A 用中证全指 985.SH 替代 | - | 第 1 章 | 数据可得性约束 |
| 微盘代码 TBD | - | 第 2 章 | 万得微盘股代码无法稳定获取 |
| 认知训练用元数据驱动 | - | 第 8 章 | 训练项 INSERT 1 行而非 ALTER |
| 异动管线时间线修订 20:30→21:00 | 2026-05-03 | 第 5 章 / 横切 | 与 L1-L8 数据就绪时间冲突修正 |
| MySQL + ClickHouse 双写落地 | 2026-05-05 | 全部 | 提升历史回算与多维分析性能 |

## 7. TBD 总账

> 各章 TBD 集中地。新对话讨论时优先消化这里。

### 高优先级（阻塞实施）
- [ ] **微盘代码**：万得微盘股代码确认或选定替代（影响第 2 章 dividend_vs_micro 因子）
- [ ] **dim_yz_seat 首批 50-100 席位**：手工录入数据来源
- [x] **业务方对 21:00 出结果延迟的最终确认**（异动管线 v1.1 已与业务方确认，21:00 出结果）
- [x] **内网服务器具体规格**（异动管线 v1.1 已选型配置：16 核 64G+ 160G SSD 存储空间）
- [x] **Redis 是否已部署**（异动管线 v1.1 前置 Redis 已部署）
- [x] **ClickHouse 部署与双写方案落地**（2026-05-05 已完成，MySQL + CK 双写就绪）
- [ ] **LLM Service (DeepSeek-V3) 实现** 可以实现（影响第 7/8 章综述生成）

### 中优先级（影响设计）
- [x] **`cn_gov_yield` 接口名**：Tushare 实测确认（第 3 章）
- [x] **L3 资金流和 L8 异动信号在云端任务的具体产出位置**（2026-05-05 已确认，云端任务产出，具体位置见 `docs/design/claude-project-files/IMPLEMENTATION_FEEDBACK.md`）
- [x] **是否单独建 `ads_l9_calendar_market` 区隔个股事件与市场事件**（第 6 章）
- [ ] **L8 评分跨板块归一**：当前未做，影响排序公平性

### 低优先级（持续迭代）
- [ ] **theme_stage_check 客观判定规则**（第 8 章，初版 manual_review）
- [ ] **outcome_inference 主线延续/扩散/切换/退潮判定规则**（第 8 章）
- [ ] **`app_daily_brief` LLM 接入成本上限**（建议 5 元/日）

## 8. 已知协作约定

- **设计在 Claude，实施在 Gemini/Antigravity**
- 给 Gemini 的接入规范：表前缀 `obs_/train_/ads_/...`、字段命名统一、async/await 全栈、Pydantic v2、JSON 日志 + request_id
- ORM：SQLAlchemy 2.x（异步）。`scripts/` 下的数据初始化或一次性运维脚本允许使用 `pymysql` 等同步库直连
- LLM 接入新建 `app/services/llm_service.py`，prompt 配置化在 `app/config/llm_prompts/{event_type}.json`
- 不新建独立 cron / Airflow，复用 `post_market_def.json` / `pre_market_prep_def.json`
- AC 即测试用例：每条 Given-When-Then AC 直接转成 Pytest 测试函数。所有测试文件必须保存在对应模块的 `scratch/` 目录，禁止污染生产代码目录

## 9. 实施反馈索引

实施侧的最新动态见 `IMPLEMENTATION_FEEDBACK.md`。

**新对话开始前必读流程**：
1. 读本文件第 5 节，确认章节状态
2. 读 `IMPLEMENTATION_FEEDBACK.md` 最近一条
3. 如涉及具体章节细节，再读对应章节的完整设计文档

## 10. 不要做的事

- 不做实时行情存储（应通过第三方 API 实时拉取）
- 不做分库分表（个人量级单库够用）
- 不做财务级精度（DECIMAL(14,2) 够用，不用整数分）
- 不接券商不下单（认知训练系统只记录意图）
- 不做用户排行榜（认知是私有的）
- 不引入 AI 自动写预判（必须用户自己输出）
- 不直接用同花顺/SW 概念分类做相变监测（噪音太大，需 RMT 去噪 + 社区发现）
- 核心算法必须用 Python 实现，CK 仅承担存储 / 列式聚合 / 时序窗口职责。CK 物化视图、ARRAY JOIN、AggregateFunction 等特有特性可用于性能优化，但不得作为算法逻辑的承载层。CK 输出给 Python 的中间结果集行数原则上控制在 **10,000 行**以内。

## 11. 部署与网络环境

- **新服务默认部署在 41 服务器**，对应编排文件 `docker-compose.node-41.yml`。禁止擅自编排到其他节点（58/111）
- **内网环境隔离**：外部 API 调用（akshare/Tushare）、SMTP 发信等跨网请求，必须配置网络代理（`.env` 中的 `HTTP_PROXY` / `HTTPS_PROXY` 或 gost 隧道），否则直接超时

## 附录：本文件维护规则

- **本文件 = 索引层**，单文件 ≤ 500 行
- 各章完整设计 = 独立 .md 文件，按需上传 project knowledge
- 实施反馈 = `IMPLEMENTATION_FEEDBACK.md` 单独维护
- TBD 销账时直接划掉本文件第 7 节对应行，不要删除（保留历史）
- 每月 review 一次，淘汰不再相关的内容

---

**变更记录**

| 日期 | 版本 | 变更 | 作者 |
|---|---|---|---|
| 2026-05-05 | v0.1 | 初稿，基于过去 17 天对话整合 | Claude 协助 |
| 2026-05-05 | v0.2 | 新增 0.1 代码仓库 / 0.2 跨网数据流;第 8 节补跨仓字段契约 | Claude 协助 |
| 2026-05-06 | v0.3 | 补充 Gate-3 审计节点、熔断器/并发安全、部署节点约束、ORM 豁免、测试隔离、CK 结果集红线,与 AGENTS.md v0.6 对齐 | Gemini 协助 |