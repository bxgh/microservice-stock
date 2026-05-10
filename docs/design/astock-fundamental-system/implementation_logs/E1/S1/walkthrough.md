# Walkthrough - E1-S1 数据源接入扩展

## 实施概述
已完成 E1-S1 (数据源接入扩展) 的全部开发与部署任务。该任务为基本面分析系统构建了核心数据底座，实现了 Tushare 财务数据的自动化同步。

## 主要变更

### 1. tushare-api 扩展
- **文件**: `tushare-api/app/services/tushare_service.py`, `tushare-api/app/api/endpoints.py`
- **内容**: 新增了资产负债表、利润表、现金流量表、财务指标及披露日历接口。
- **处理**: 实现了针对 Tushare `频率超限` 错误（200次/分钟）的自动退避重试机制。

### 2. 数据库部署 (ODS 层)
- **文件**: `migrations/20260509_create_ods_financial_tables.sql`
- **成果**: 创建了 `ods_fin_balancesheet`, `ods_fin_income`, `ods_fin_cashflow`, `ods_fin_indicators` 四张标准表。
- **治理**: 严格对齐 v1.2 规范，包含 `ts_code`, `end_date` 索引及 `is_deleted` 审计字段。

### 3. stock-manager-api 集成
- **文件**: `stock-manager-api/app/services/financial_data_service.py`
- **功能**: 
    - 封装了 Tushare 数据拉取与清洗逻辑（日期格式化、字段映射）。
    - 实现了 `ON DUPLICATE KEY UPDATE` 幂等入库。
- **调度**: 在 `stock-manager-api/app/scheduler/jobs.py` 中注册了 `daily_financial_data_sync_job`，每日 18:30 自动触发。

## 验证结果

### 1. 物理查验 (True Source)
执行 `scratch/verify_sync.py` 确认数据已成功落库：
```text
Total records in ods_fin_balancesheet: 5413 (同步中...)
Sample data: (('000513.SZ', datetime.date(2026, 3, 31), Decimal('24193940942.9700')), ...)
```

### 2. 自动化测试
- [x] 接口连通性验证: Tushare API 返回 200。
- [x] 逻辑验证: 成功处理 `total_liab` -> `total_liabilities` 等字段映射。

## 问题修复与数据维护 (2026-05-10)

### 1. 现金流量表映射修复
- **问题**: `FinancialDataService.sync_cashflow` 缺失字段映射，导致 `net_cash_flows_oper_act` 等字段入库为 NULL。
- **修复**: 在 `stock-manager-api` 中增加了 Tushare 字段到 ODS 字段的显式映射。
- **修复脚本**: 编写并执行了 `scripts/repair_cashflow_history.py`。
- **状态**: 正在后台全量修复现金流量表历史数据。

## 当前状态
- **后台任务**: `scripts/repair_cashflow_history.py` 正在修复现金流量表数据。
- **数据总量**: 
    - 资产负债表: 25.5万+
    - 利润表: 30.9万+
    - 现金流量表: 27.8万+ (修复中)
    - 财务指标: 23.3万+
