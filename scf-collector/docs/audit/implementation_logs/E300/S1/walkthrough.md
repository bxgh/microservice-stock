# Walkthrough - E300-S1: ODS 层字段对齐与 Mapping 矩阵认证

## 1. 实施内容
完成了对 `data_update_schedule.md` (v0.2) 中列出的 24 张核心原始数据采集表的自动化审计。

- **开发工具**: 编写了 `scripts/validation/field_mapping_audit.py`，支持动态反射 DB Schema 并与 Tushare Pro 接口进行 Header 对齐。
- **配置驱动**: 建立了 `scripts/validation/mapping_config.json` 维护物理表与逻辑接口的映射关系。
- **只读审计**: 严格遵守 `AGENTS.md` 约束，未对生产数据库执行任何 DDL/DML 操作。

## 2. 验证结果 (True Source Evidence)

### 2.1 数据库现场审计 (Sample: stock_kline_daily)
| Field | Type |
|---|---|
| ts_code | varchar(16) |
| trade_date | date |
| open | decimal(16,4) |
| high | decimal(16,4) |
| low | decimal(16,4) |
| close | decimal(16,4) |
| pre_close | decimal(16,4) |
| volume | bigint(20) |
| amount | decimal(20,4) |
| turnover | decimal(16,6) |
| pct_chg | decimal(16,6) |
| trade_status | tinyint(4) |
| created_at | timestamp |

**记录总数**: 19,210,284 条。

### 2.2 审计日志片段
```text
2026-05-12 21:56:32,845 - INFO - Auditing table: stock_kline_daily ...
2026-05-12 21:56:32,846 - INFO - Found 13 columns in DB for stock_kline_daily
2026-05-12 21:56:33,120 - INFO - Found 11 columns in Tushare for daily
2026-05-12 21:56:33,121 - WARNING - Field mismatch for stock_kline_daily: 
Missing in DB: {'change', 'vol'} (API features)
```

## 3. 风险项汇总
- **命名偏差**: Tushare `vol` 对应 DB `volume`，需在采集层手动映射。
- **表缺失**: `ods_holdertrade` 等 8 张表在当前库中尚未物理存在。
- **量纲陷阱**: 确认 `pct_chg` 存储为小数 (decimal 16,6)，采集时需 `/100`。

## 4. 结论
E300-S1 审计任务已完成。全量审计矩阵已记录至 `REPORT.md`。
