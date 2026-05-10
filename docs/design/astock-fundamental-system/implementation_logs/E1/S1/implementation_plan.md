# Implementation Plan - E1-S1 数据源接入扩展

## 需求解析
在现有的 `tushare-api` 中增加财务三报表接口，并在 `stock-manager-api` 中封装同步逻辑，确保基本面分析所需的原始财务事实数据（Fact）能够每日自动增量同步并支持历史回填。

## 依赖认证
- [x] **数据源**: Tushare Pro 积分已满足 2000+ 积分要求（`forecast` 接口已在使用）。
- [x] **环境**: 腾讯云 MySQL 5.7 与 ClickHouse 环境已就绪。
- [x] **治理**: 需严格遵守 `AGENTS.md` 中的 `ods_` 前缀与审计字段规范。

## 角色激活
- **Role**: Python Backend Engineer / Data Engineer
- **Focus**: Async I/O, Data Integrity, Schema Governance

## 方案设计

### 1. tushare-api 扩展
在 `tushare-api` 的 `TushareService` 中补充财务相关接口调用。

#### [MODIFY] [tushare_service.py](file:///home/ubuntu/microservice-stock/tushare-api/app/services/tushare_service.py)
- 新增 `get_balancesheet`: 资产负债表
- 新增 `get_income`: 利润表
- 新增 `get_cashflow`: 现金流量表
- 新增 `get_fina_indicator`: 财务指标
- 新增 `get_disclosure_date`: 财报披露日期

### 2. 数据库标准化 (DDL)
创建符合 v1.2 规范 of ODS 层财务表。

#### [NEW] [20260509_create_ods_financial_tables.sql](file:///home/ubuntu/microservice-stock/migrations/20260509_create_ods_financial_tables.sql)
- `ods_fin_balancesheet`
- `ods_fin_income`
- `ods_fin_cashflow`
- `ods_fin_indicators`
- 所有表必须包含 `created_at`, `updated_at`, `is_deleted` 字段。

### 3. stock-manager-api 同步逻辑
封装业务层服务，处理 API 调用与数据库持久化。

#### [NEW] [financial_data_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/financial_data_service.py)
- 实现 `sync_financial_statements(ts_code, period)`
- 实现批量入库逻辑，确保幂等性（`ON DUPLICATE KEY UPDATE`）。

#### [MODIFY] [jobs.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/scheduler/jobs.py)
- 新增 `daily_financial_data_sync_job`: 每日扫描披露日历并同步新发布的报表。

### 4. 历史回填脚本
#### [NEW] [init_financial_history.py](file:///home/ubuntu/microservice-stock/scripts/init_financial_history.py)
- 负责 2010 年至今的财务数据初始化。
- 支持按行业或按时间范围分批次拉取，避免 Tushare 限频。

## 验证计划

### 自动化测试
1. **接口验证**: `pytest tests/test_tushare_finance.py` 验证 API 返回格式。
2. **同步验证**: 执行同步脚本后，通过 SQL 查询 `ods_fin_balancesheet` 确认 `is_deleted` 等字段正确填充。

### 手动校验
- 抽样对比 Tushare 官网数据与数据库中 `net_profit`、`total_assets` 等关键字段，容差 ≤ 0.01%。
