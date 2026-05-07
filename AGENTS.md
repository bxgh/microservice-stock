# AGENTS.md — A 股盘后系统(内网仓)实施约束

> 本文件是 Gemini / Antigravity 在本仓实施时**永远生效**的硬约束。任何指令冲突时,本文件的规则**优先于通用最佳实践和 LLM 偏好**。
>
> 设计层文档(`docs/PROJECT_OVERVIEW.md` 等)是 source of truth,本文件只提炼实施侧每行代码都要遵守的规则。

---

## 1. 项目认知

**仓库角色**:本项目(GitHub 仓名为 `microservice-stock-ck`,本地目录通常为 `microservice-stock`)是 A 股盘后分析系统的**内网计算 + 双写仓**。

- 数据上游:腾讯云仓 `bxgh/microservice-stock` 通过跨网同步推送 `ods_*` 表
- 本仓职责:计算 `dwd_*` / `ads_*` / `app_*` / `dim_*` / `obs_*` / `train_*` 层
- 数据下游:双写到 ClickHouse(本地,历史回算)+ MySQL(回流到云端,供 wxch-gateway 给小程序读)
- 设计 source of truth:`docs/PROJECT_OVERVIEW.md` / `docs/TABLES_INDEX.md`

**协作分工**:
- 设计在 Claude(Anthropic),交付为 `docs/` 下 Markdown 文档(Epic-Story-Task-AC 结构)
- 实施在 Gemini(本仓),按文档写代码
- **不要反向修改 `docs/PROJECT_OVERVIEW.md` / `TABLES_INDEX.md`**;实施过程文档(Plan/Task/Walkthrough)仅在本地保存于**对应设计文档同目录**下的 `implementation_logs/E{N}/S{M}/` 文件夹内,`docs/IMPLEMENTATION_FEEDBACK.md` 仍作为全局进度索引。

---

## 2. 技术栈硬约束

- 数据库:**MySQL 5.7**(不是 8.0)+ ClickHouse(双写)
- Python:async/await 全栈、Pydantic v2 模型、JSON 日志 + `request_id`
- ORM:SQLAlchemy 2.x(异步)。(例外:`scripts/` 下的数据初始化或一次性运维脚本,允许使用 `pymysql` 等同步库直连)
- 调度: APScheduler + 自研 JSON pipeline(`post_market_def.json` / `pre_market_prep_def.json`)。**不引入 Airflow / 独立 cron**
- 通知规范: 所有定时任务(Task)和工作流(Workflow)完成或失败时,**必须**触发标准格式的邮件报告(`send_task_report` / `send_workflow_report`)。报告须包含执行时长、处理行数(processed_count)及错误摘要。
- DDL 管理:所有 schema 变更进 `migrations/`,Alembic 或独立 SQL 脚本,**禁止内嵌业务代码**
- 字符集:`utf8mb4` + `utf8mb4_unicode_ci` + `ROW_FORMAT=DYNAMIC`,新表必须显式声明
- LLM 接入:统一走 `app/services/llm_service.py`,prompt 配置化在 `app/config/llm_prompts/{event_type}.json`

---

## 3. 命名规范(强制)

### 3.1 表前缀

| 前缀 | 用途 | 写入方 | 关键约定 |
|---|---|---|---|
| `ods_` | 原始数据层 | 云端采集 | **永不修改**,只能 TRUNCATE 重灌 |
| `dwd_` | 明细层 | 本仓 | 清洗 / 脱敏后明细 |
| `dim_` | 维度表 | 手工 / 批量 | 字典 / 基础信息 |
| `ads_` | 应用数据层 | 本仓 | 每日聚合指标 |
| `app_` | 应用面表 | 本仓 | 前端直查专用 |
| `obs_` | 观察点系统 | 本仓 | 第 9 章专属 |
| `train_` | 认知训练系统 | 用户 / 本仓 | 第 8 章专属 |
| `meta_` | 系统元数据 | 系统 | 调度 / 契约 |

**禁止**:新表使用 `stock_*` / `daily_*` / `raw_*` / `sys_*` 前缀(legacy)。如需用 legacy 表名,先在 PR 标题写「使用 legacy 命名:<理由>」。

### 3.2 字段命名

| 必须用 | 不要用 |
|---|---|
| `ts_code` (VARCHAR(20)) | `stock_code` / `code` |
| `symbol` (VARCHAR(10)) | (symbol 专指纯数字代码,跟 ts_code 是两个字段) |
| `trade_date` (DATE) | `dt` / `date` / `t_date` |
| `pct_chg` (DECIMAL(10,6)) | `pct` / `change_pct` / `chg` |
| `amount` (DECIMAL(20,2)) | `vol` / `volume` (成交额/成交量) |
| `volume` (BIGINT) | 成交量 (股)。注：`stock_kline_daily` 历史表单位为“股”，而非“手” |
| `created_at` / `updated_at` | `ctime` / `mtime` / `create_time` |
| `is_deleted` (TINYINT(1)) | `deleted` / `is_del` |

### 3.3 表结构尾部三件套(强制)

每张新表必须包含:

```sql
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
is_deleted TINYINT(1) NOT NULL DEFAULT 0,
KEY idx_updated_at (updated_at)
```

`idx_updated_at` 用于增量同步,不能省。

### 3.4 查询必须过滤软删除

任何查询业务表的 SQL,WHERE 子句必须包含 `is_deleted = 0`。**没有默认行为兜底**,漏写就是 bug。

### 3.5 数据质量与防线融合

盘后批处理极度依赖上游数据质量。在执行 T+0 核心数据写入前,必须验证或等待 **Gate-3(盘后审计 / Sync Consistency Audit)** 校验通过,确保 MySQL 与 ClickHouse 双写记录一致且无脏数据。

---

## 4. 单位陷阱(高频踩坑,采集 / 计算 / 应用层都涉及)

| 字段 | 入库规范 | 上游格式 | 强制处理 |
|---|---|---|---|
| `pct_chg` | 小数(0.0123 = 1.23%) | 通常已是小数 | 采集层 sanity check `if value > 1: log.warn`,异常告警 |
| `holdertrade.change_ratio` | 小数 | **不稳定**(百分比/小数交替) | 采集层强制 `if value > 1: value /= 100` |
| ETF `share_chg` | 亿份 | 直接存 | 净申购金额 = `share_chg * nav * 1e8`(单位:元) |
| `yield_pct`(国债) | 小数 | 上游百分比 | 采集层 `/100` |
| `amount`(成交额) | 元 | Tushare 千元 / akshare 元 | 各源单独适配,统一为元 |
| `discount_pct`(大宗) | 小数,**正数 = 溢价** | - | 同 pct_chg 规则 |

**ETF 净申购金额漏乘 `1e8` 是历史 bug 重灾区**。任何涉及 ETF 净申购的计算都要 grep 一遍 `1e8`。

---

## 5. MySQL 5.7 限制(必须知道)

| 不可用 | 替代 |
|---|---|
| 窗口函数(`OVER`) | 自连接 + `(SELECT COUNT(*) ...)` 子查询 |
| CTE(`WITH ...`) | 派生表(`SELECT * FROM (SELECT ...) t`) |
| CHECK 约束 | 业务校验放应用层(Pydantic v2) |
| JSON 路径索引 | 高频查询字段冗余成独立列,JSON 字段只存低频/扩展信息 |

⚠️ **不进生产代码的写法**:
- `@变量赋值` 依赖 `ORDER BY` 隐性行为,8.0 升级会失效。仅一次性报表可用,生产代码用自连接
- 跨数据库 JOIN(MySQL ↔ ClickHouse)不支持,应用层合并

---

## 6. 业务领域口径(A 股专属)

### 6.1 涨跌停

- **当前简化版**:全部按主板 9.7% 判定(留 0.3% 浮点误差缓冲)
- 实际板块差异:主板 10% / 创业板 / 科创板 20% / 北交所 30% / ST 5%
- 简化版副作用已知,**前端必须注明「按主板 9.7% 简化判定」**
- `ods_event_limit_pool.pool_type ∈ {zt, dt, zb, lian}`(涨停 / 跌停 / 炸板 / 连板)
- `board_height`:首板 = 1,二连 = 2,N 连 = N

### 6.2 北向资金(2024-08-19 重大变更)

- **整体北向**:仅日终,走 `stock_north_funds_daily.net_buy_amount`
- **个股北向**:北向资金 2024-08-19 起港交所不再披露盘中实时数据,仅日终成交净额。**个股北向已无法获取,跨期不可比**。
- **外部接口防护**:针对 akshare/Tushare 等的三方限速与网络抖动,**必须强制实现 CircuitBreaker(熔断器)和 RetryPolicy(重试机制)**。
- **并发状态安全**:任何涉及共享状态(如连接池、内存字典)的修改,必须使用 `asyncio.Lock()` 保障并发安全。

### 6.3 行业分类(申万)

- 本项目**只用申万**,不混用中信
- 默认行业涨跌排行用申万 l1(31 个粒度)
- 细分用 l2(120 个粒度),l3 暂不接入
- 用户提到「中信医药」「中信电子」时,**先停下来确认是否切体系**,不要默认翻译为申万

### 6.4 交易日历(`meta_trading_calendar`,legacy: `trade_cal`)

- **必须**用 `pre_trade_date` / `next_trade_date` 字段链路做日期跳转
- **绝不**用日历日加减(跨周末 / 长假错位)
- 「上市 ≥ 60 个交易日」:从 `list_date` 起数 60 个 `is_open=1` 的日期
- 「过去 N 个交易日」:`WHERE cal_date <= ? AND is_open=1 ORDER BY cal_date DESC LIMIT N`

### 6.5 ST 状态差分

- 跨周末 / 长假**不能**直接用「今日 - 上交易日」做 diff
- 正确做法:先用「股票名称包含 `ST` 或 `*ST`」全表对照得到当前 ST 集合,再与昨日集合做差集 / 并集
- `ods_st_change.change_date` 字段在长假后可能延迟 1-2 日,**不能依赖**

### 6.6 概念分类(akshare / 同花顺)

- 半数概念 < 10 只成分股,统计无意义。**默认过滤** `member_count >= 10`
- 同名多版本(机器人 / 机器人概念 / 人形机器人)需要消歧
- **不要**直接用同花顺概念分类做相变监测,噪音太大

### 6.7 大宗 / ETF / 龙虎榜

- 大宗 `discount_pct`:**正数 = 溢价**,负数 = 折价
- ETF 净申购金额:`share_chg * nav * 1e8`(单位:元)
- 龙虎榜游资识别:仅当 `dim_yz_seat.yz_type='top_yz'`,通过 `dim_yz_seat.aliases` (JSON) 做别名匹配,目标命中率 > 90%

### 6.8 万得全 A 替代

涉及「全 A」一律用中证全指 `985.SH`,不要用 `881001.WI` 或其他代号。

### 6.9 微盘股(TBD)

万得微盘股代码 TBD,缺失时第 2 章风格因子降级为 3 因子(跳过 `dividend_vs_micro`)。**不要用其他微盘指数硬替代**,会污染因子。

---

## 7. ClickHouse 与 MySQL 的边界

| 场景 | 走哪边 | 理由 |
|---|---|---|
| T+0 跑批写入 | MySQL(双写到 CK) | 事务保证 + 幂等 |
| 历史回算(全 A × 多年) | ClickHouse | 列存性能 |
| 单股票详情(小程序) | MySQL | 索引优化 |
| 多维聚合(行业 / 概念分布) | ClickHouse | OLAP |
| 多表 JOIN 复杂查询 | MySQL | CK JOIN 性能差 |
| 时序窗口指标(MA / RSI / 分位数) | ClickHouse | 天然支持窗口函数 |
| 前端 API 直查 | MySQL(via wxch-gateway) | 云端 MySQL,内网 CK 不暴露 |

**分工边界及性能红线**:
- **Python 职责**: 承载业务判定逻辑（评分、阈值、规则、状态机、可解释文案生成）。
- **ClickHouse 职责**: 承担存储 + 大批量聚合 + 时序窗口 + 多表 JOIN 的数据准备职责。
- **边界量化**: 两层分工边界以「CK 输出给 Python 的中间结果集行数」衡量,原则上控制在 **10,000 行**以内（即便输入是千万级）。
- **优化手段**: 物化视图、ARRAY JOIN、AggregateFunction 等可用于性能优化,但不得作为算法逻辑承载层。

---

## 8. 跨仓 schema 变更(强制流程)

任何修改跨仓表 schema(`ods_*` / `ads_*` / `app_*`)的 PR,必须:

1. 在 `docs/IMPLEMENTATION_FEEDBACK.md` 追加一条「跨仓 schema 变更:仓 A → 仓 B」
2. 列出影响的下游消费方(查 `docs/TABLES_INDEX.md` 第 11 节跨表依赖速查)
3. 提供 migration 脚本 + rollback 脚本(双写架构必须 rollback)
4. PR 描述 @ 对侧仓的 owner

漏任何一项,PR **不能合**。

---

## 9. 文档协作(Epic-Story-Task-AC 结构)

`docs/` 下设计文档使用 `Epic → Story → Task → AC(Given-When-Then)` 结构。实施时:

1. **AC 即测试用例**:每条 Given-When-Then AC 直接转成对应测试函数
   - Given → fixture / setup
   - When → 被测调用
   - Then → assert
2. **Task ID 进 commit message**:每个 task 一个 commit,前缀 `[E1-S1-T1]`
3. **验收前必跑 AC**:实施完一个 Story 必须先跑全部 AC 通过再写下一个 Story。所有测试文件**必须保存在对应模块的 `scratch/` 目录**中,禁止污染生产代码目录。
4. **遇到 TBD 停下**:文档标 TBD 的字段 / 接口名 / 实现细节,**不允许编造**。两种处理:
   - 在 `IMPLEMENTATION_FEEDBACK.md` 标注后等设计侧补
   - 或在 PR 描述里明确「按 X 假设实施,待设计侧确认」,设计侧确认后销账
5. **跨章节字段引用**:用其他章节字段(如 `ads_l8.has_yz_seat`)前必须先查 `TABLES_INDEX.md`,确认字段存在 + 单位一致
6. **强制进度同步**:每完成一个 Task,必须回填设计文档中的任务状态(`- [ ]` -> `- [x]`);每完成一个 Story,必须更新 `docs/IMPLEMENTATION_FEEDBACK.md` 中的全局进度。防止文档与代码实现脱节。

---

## 10. 反模式清单(自检)

写代码 / SQL / DDL 前,以下错误必须避免:

- ❌ 字段命名用 `stock_code` / `dt` / `pct`(应为 `ts_code` / `trade_date` / `pct_chg`)
- ❌ 漏 `is_deleted = 0` 过滤
- ❌ `pct_chg` 当百分比处理(全库一律小数)
- ❌ ETF 净申购金额漏 `* 1e8`
- ❌ 跨长假用日历日加减取上一交易日
- ❌ 用了 MySQL 8.0 才有的窗口函数 / CTE / CHECK 约束
- ❌ JSON 路径查询直接进生产 SQL
- ❌ `ods_*` 表上跑 UPDATE / DELETE
- ❌ 涉及个股北向数据(2024-08-19 后已停发)
- ❌ 涨跌停判定混合板块阈值(简化版统一 9.7%)
- ❌ 申万和中信行业混用
- ❌ `SELECT *`(明确列出字段,便于 schema 变更追踪)
- ❌ 隐式类型转换:`WHERE ts_code = 600519`(缺引号导致全表扫)
- ❌ 大表 `OFFSET N LIMIT M` 当 N 很大(改用主键游标)
- ❌ 没跑 AC 通过就进入下一个 Story
- ❌ TBD 字段用编造的接口名 / 字段名 / 默认值填补
- ❌ 跨仓 schema 变更不通知对侧

---

## 11. 不做的事(明确边界)

- ❌ 不做实时行情存储(应通过第三方 API 实时拉取)
- ❌ 不做分库分表(单库够用)
- ❌ 不做财务级精度(DECIMAL(14,2) 够用,不用整数分)
- ❌ 不接券商不下单(认知训练系统只记录意图)
- ❌ 不在 `ods_*` 表上做 UPDATE / DELETE
- ❌ 不引入新数据源 / 新章节(除非 `PROJECT_OVERVIEW.md` 第 5 节有对应章节)
- ❌ 不重命名表 / 字段(命名变更须通过设计文档冻结,实施侧不主动改)
- ❌ 不删除 legacy 表(`stock_kline_daily` 等暂不迁移,与新表共存)
- ❌ 不在生产 SQL 里写硬编码业务魔数(涨跌停 9.7% 等放配置)
- ❌ 不写跨数据库的存储过程 / 触发器(逻辑放应用层)
- ❌ 不在 DDL 里写中文表名 / 字段名

---

## 12. 部署与网络环境约束(强制)

- **服务部署节点**:本项目跨多个物理节点(41/58/111)。**所有新开发的服务,默认必须部署在 41 服务器**,对应编排文件为 `docker-compose.node-41.yml`。禁止擅自将服务编排到其他节点。
- **网络隔离与代理**: 由于内网环境隔离, 任何涉及**外部 API 调用**(如 akshare/Tushare 等外部网关)、**SMTP 邮件发信**等跨网请求, **必须配置网络代理**(如读取 `.env` 中的 `HTTP_PROXY` / `HTTPS_PROXY` 或配置 gost 隧道)。注：直接部署在腾讯云等可访问外网的服务器时无需配置。

---

**变更记录**

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-05-06 | v0.1 | 初版 |
| 2026-05-06 | v0.2 | 明确实施过程文档按 Story 切分子目录本地保存, IMPLEMENTATION_FEEDBACK.md 作为索引。 |
| 2026-05-06 | v0.3 | 移除实施记录必须同步到 Git 的约束。 |
| 2026-05-06 | v0.4 | 将实施日志存放路径修改为相对于对应设计文档的动态路径。 |
| 2026-05-06 | v0.5 | 量化 Python 与 ClickHouse 的分工边界,引入 10,000 行结果集红线。 |
| 2026-05-06 | v0.6 | 增加部署节点(41服务器)与网络代理约束，完善熔断器、Gate-3与ORM豁免规则。 |


