# E1 数据基础设施 (重整版)

> **现状评估**: 项目已具备 `tushare-api`、`akshare-api` 及成熟的 `stock-manager-api` 同步机制。MySQL 5.7 与 ClickHouse 已投产。
> **重整目标**: 将现有的分散财务同步逻辑整合进标准化的 `ods_*` 层，并新增公告全文抓取能力。

构建本地化数据底座,所有后续分析依赖此层。**核心原则:数据全部本地化,不在分析时实时拉取**。预计耗时 1 周 (基于已有设施)。

## E1-S1 数据源接入扩展

**作为** 系统数据管理员,**我希望** 在现有 `tushare-api` 中增加财务三报表接口，并统一由 `stock-manager-api` 调度,**以便** 补齐基本面分析所需的原始 Fact 数据。

### 任务

- E1-S1-T1 (已完成) 申请 Tushare Pro 账号并获取 API token。
- E1-S1-T2 (MODIFY) 扩展 `tushare-api` 的 `TushareService`，增加 `balancesheet`, `income`, `cashflow`, `fina_indicator` 接口。
- E1-S1-T3 (NEW) 在 `stock-manager-api` 中封装 `FinancialDataService`，支持从 Tushare 增量拉取报告期数据。
- E1-S1-T4 (MODIFY) 升级历史回填脚本 `init_history.py`，专门负责 2010 年至今的财务三报表及核心指标的全量补齐。
- E1-S1-T5 (REUSE) 复用现有的 `_execute` 异步封装与限频重试机制。

### 验收标准

- **AC1**: 财务数据增量同步
  - **Given** 公司发布新财报
  - **When** 每日定时任务触发
  - **Then** 自动拉取并存入 `ods_financial_balancesheet` 等表，数据偏差 ≤ 0.01% (与 Tushare 官网对比)

---

## E1-S2 数据库标准化与 Schema 演进

**作为** 系统架构维护者,**我希望** 将现有的 `stock_balance_sheet` 等旧表规范化为 `ods_*` 系列，并补充审计字段,**以便** 满足 v1.2 治理要求。

### 任务

- E1-S2-T1 (REUSE) 现有的腾讯云 MySQL 5.7 和 ClickHouse 环境。
- E1-S2-T2 (STRICT) 强制执行 `ods_*` 命名规范。将旧表数据迁移至新表（如 `ods_fin_balancesheet`）。
- E1-S2-T3 (DDL) 编写 DDL 补齐 `created_at`, `updated_at`, `is_deleted` 及其索引（详见 `AGENTS.md`）。
- E1-S2-T4 (REUSE) 现有的内网 Slave 容灾架构。
- E1-S2-T5 (NEW) 在 ClickHouse 中建立财务宽表物化视图，支持跨季度同比/环比秒级查询。

### 验收标准

- **AC1**: 核心表规范化
  - **Given** 执行 DDL 变更
  - **Then** 所有基本面相关表必须包含 `is_deleted` 字段，且默认为 0。

---

## E1-S3 公告/纪要全文抓取 (New Layer)

**作为** AI 抽取层的上游,**我希望** 全量抓取年报、季报、调研纪要、业绩说明会的 PDF 原文并归档,**以便** L3 层可以基于全文做结构化抽取。

### 任务

- E1-S3-T1 编写巨潮资讯网爬虫,抓取年报/半年报/季报 PDF (新增 `crawler-service`)
- E1-S3-T2 抓取业绩说明会纪要(投资者关系互动平台)
- E1-S3-T3 抓取机构调研纪要(深交所互动易、上交所 e 互动)
- E1-S3-T4 PDF 文本提取(用 `pdfplumber` 或 `PyMuPDF`)并存储为 Markdown
- E1-S3-T5 文件归档命名规范:`{ts_code}_{report_type}_{report_period}.md`,存储路径 `/data/disclosures/`

### 验收标准

- **AC1**: 年报抓取覆盖率
  - **Given** 半导体 + 生物合成研究池(预计 ~200 只)
  - **When** 执行 `fetch_annual_reports.py --year 2024`
  - **Then** 抓取覆盖率 ≥ 95%

---

## E1-S4 数据质量与契约集成

**作为** 系统使用者,**我希望** 财务数据接入自动触发 `meta_data_readiness` 信号,**以便** 后续 AI 抽取任务能够基于事件驱动。

### 任务

- E1-S4-T1 (REUSE) 现有 `data_readiness` 机制。
- E1-S4-T2 在财务同步完成后，自动向 `meta_data_readiness` 插入就绪状态。
- E1-S4-T3 (NEW) 跨源校验：对比 Tushare 与 AkShare 的净利润、净资产关键字段，差异 > 1% 则告警。
- E1-S4-T4 异常告警通过已有的邮件 / Bark 系统推送。

### 验收标准

- **AC1**: 事件驱动链路
  - **Given** 财务报表同步完成
  - **Then** `meta_data_readiness` 出现对应记录，状态为 `READY`
DF 原文并归档,**以便** L3 层可以基于全文做结构化抽取。

### 任务

- E1-S3-T1 编写巨潮资讯网爬虫,抓取年报/半年报/季报 PDF
- E1-S3-T2 抓取业绩说明会纪要(投资者关系互动平台)
- E1-S3-T3 抓取机构调研纪要(深交所互动易、上交所 e 互动)
- E1-S3-T4 PDF 文本提取(用 `pdfplumber` 或 `PyMuPDF`)并存储为 Markdown
- E1-S3-T5 文件归档命名规范:`{ts_code}_{report_type}_{report_period}.md`,存储路径 `/data/disclosures/`

### 验收标准

- **AC1**: 年报抓取覆盖率
  - **Given** 半导体 + 生物合成研究池(预计 ~200 只)
  - **When** 执行 `fetch_annual_reports.py --year 2024`
  - **Then** 抓取覆盖率 ≥ 95%,失败的股票输出到 `failed_list.txt`(可能由于公告未披露、PDF 解析失败等),手工兜底

- **AC2**: PDF 文本提取质量
  - **Given** 一份 100 页年报 PDF
  - **When** 执行文本提取
  - **Then** 提取后的 Markdown 文本中"管理层讨论与分析"章节完整,表格保留为 Markdown 表格格式,提取时长 ≤ 30 秒

- **AC3**: 增量更新
  - **Given** 系统已运行,某公司发布新年报
  - **When** E1-S1 检测到新披露事件
  - **Then** 自动触发该公司年报抓取,30 分钟内完成抓取 + 文本提取 + 归档

---

## E1-S4 数据质量校验

**作为** 系统使用者,**我希望** 数据异常被自动发现和告警,**以便** 不会基于错误数据做错误判断。

### 任务

- E1-S4-T1 编写每日数据质量校验脚本(空值检查、异常值检查、跨源对比)
- E1-S4-T2 Tushare vs akshare 关键字段交叉验证(如收盘价、市值)
- E1-S4-T3 财报数据勾稽校验(资产 = 负债 + 所有者权益等基础恒等式)
- E1-S4-T4 异常告警通过邮件 / Bark 推送

### 验收标准

- **AC1**: 跨源价格校验
  - **Given** 当日行情已同步完成
  - **When** 触发 `qc_price_cross_check.py`
  - **Then** Tushare 与 akshare 收盘价偏差 > 1% 的股票输出到告警列表,推送至预设邮箱

- **AC2**: 财报恒等式校验
  - **Given** 新披露的财报数据已入库
  - **When** 触发 `qc_financial_identity.py`
  - **Then** 资产 ≠ 负债 + 所有者权益(误差 > 1 万元)的报告记录到 `meta_qc_alerts` 表,人工复核后标记 resolved/wontfix
