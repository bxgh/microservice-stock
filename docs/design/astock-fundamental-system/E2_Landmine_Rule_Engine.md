# E2 排雷规则引擎

用纯 SQL 规则把全市场从 5300+ 过滤到研究池候选(约 2000-3000 只),无需 AI 介入。预计耗时 1 周。

## E2-S1 排雷指标计算

**作为** 研究员,**我希望** 系统每周自动计算全市场所有股票的排雷指标,**以便** 我能快速排除存在重大基本面瑕疵的标的。

### 任务

- E2-S1-T1 实现排雷指标计算 SQL(每个指标一个 view 或物化表)
- E2-S1-T2 商誉/净资产比例计算
- E2-S1-T3 经营现金流/净利润比例(3 年均值)
- E2-S1-T4 应收账款周转天数同比变化
- E2-S1-T5 大股东质押比例(从十大股东数据计算)
- E2-S1-T6 审计意见标识抽取(从年报披露文件)
- E2-S1-T7 退市风险警示标识(ST、*ST 状态)

### 验收标准

- **AC1**: 全市场指标计算
  - **Given** 最新一期财报数据已入库
  - **When** 执行 `compute_landmine_indicators.sql`
  - **Then** 全部 A 股(剔除上市未满 1 年的新股)的 7 项排雷指标全部计算完成,结果写入 `ads_landmine_indicators` 表,完成时间 ≤ 5 分钟

- **AC2**: 阈值规则触发
  - **Given** `ads_landmine_indicators` 表已更新
  - **When** 执行 `evaluate_landmine_rules.sql`
  - **Then** 触发任一阈值的股票被标记 `is_landmine=1`,触发原因记录在 `landmine_reasons` 字段(JSON 数组),如 `["goodwill_ratio_high", "audit_qualified"]`

- **AC3**: 阈值可配置
  - **Given** 阈值定义在 `config/landmine_rules.yaml`
  - **When** 修改商誉比例阈值从 0.30 改为 0.25
  - **Then** 重新执行评估后,新触发的股票被正确识别,无需修改 SQL 代码

---

## E2-S2 全市场每周扫描调度

**作为** 系统使用者,**我希望** 排雷扫描每周自动执行,**以便** 我无需手动触发。

### 任务

- E2-S2-T1 配置每周一早上 6:00 自动调度(crontab 或 APScheduler)
- E2-S2-T2 扫描结果生成对比报告(本周新增触发、本周解除触发的股票列表)
- E2-S2-T3 关键变化推送(如某只研究池中的股票首次触发,需立即告警)

### 验收标准

- **AC1**: 定时执行
  - **Given** 系统部署在腾讯云,每周一 06:00 自动触发
  - **When** crontab 调度生效
  - **Then** 排雷扫描在 06:30 前完成,结果文件 `landmine_report_YYYYMMDD.md` 生成在 `/data/reports/landmine/`

- **AC2**: 研究池告警
  - **Given** 研究池中的某只股票本周首次触发排雷
  - **When** 扫描完成
  - **Then** 立即推送告警邮件,内容包含股票代码、名称、触发原因、对比上周的具体变化数据

---

## E2-S3 排雷结果归档与变化跟踪

**作为** 研究员,**我希望** 每周排雷结果有历史归档,**以便** 我可以追溯某只股票的排雷状态变化。

### 任务

- E2-S3-T1 设计 `obs_landmine_history` 表,按周快照存储
- E2-S3-T2 实现"某只股票最近 6 个月排雷状态变化"的查询接口
- E2-S3-T3 排雷状态变化的可视化(简单的 Markdown 表格输出)

### 验收标准

- **AC1**: 历史快照
  - **Given** 排雷扫描已运行 4 周
  - **When** 查询 `select * from obs_landmine_history where ts_code='000001.SZ' order by snap_date desc`
  - **Then** 返回 4 条记录,每条包含 `is_landmine` 标志和 `landmine_reasons` 详情
