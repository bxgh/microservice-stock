# Implementation Plan - E7-S1: 基础元数据云端同步 (Meta Foundation)

实现从 CVM 脚本向 SCF 微服务的迁移，建立云端“真源”基础元数据同步体系。

## User Review Required

> [!IMPORTANT]
> 1. **独立 SCF 部署**: 本计划将引入一个新的 SCF 函数 `stock-scf-meta`。
> 2. **定时触发器**: 需要在腾讯云控制台配置两个定时触发器：
>    - 每日 08:30 (Calendar Sync)
>    - 每日 09:00 (StockList Sync)
> 3. **表名约定**: 保持所有现有 MySQL 数据库表名和结构不变，直接使用 `trade_cal` 和 `stock_basic_info`。

## Open Questions

- [x] 是否现在就执行 `trade_cal` 到 `meta_trading_calendar` 的物理重命名？ -> **结论**: 保持现状，逻辑层兼容。
- [ ] 股票列表同步是否需要包含行业分类 (Industry)？PRD 提到 AC2 包含行业分类。

## Proposed Changes

### `scf-collector` Component

#### [MODIFY] [tushare_cl.py](file:///e:/gitee/microservice-stock/scf-collector/shared/collectors/tushare_cl.py)
- 新增 `fetch_trading_calendar(start_date, end_date)` 方法。
- 新增 `fetch_stock_list()` 方法（包含 `list_status='L'` 等参数）。

#### [MODIFY] [dao.py](file:///e:/gitee/microservice-stock/scf-collector/shared/db/dao.py)
- 新增 `save_trading_calendar(data)`：批量更新 `trade_cal` (Upsert 逻辑，需进行日期格式转换)。
- 新增 `save_stock_list(data)`：批量更新 `stock_basic_info` (Upsert 逻辑)。

#### [NEW] [meta_index.py](file:///e:/gitee/microservice-stock/scf-collector/meta_index.py)
- 新的 SCF 入口文件。
- **环境适配**: 头部强制重定向 `HOME` 和缓存目录至 `/tmp`（遵守 `scf-deployment` 规范，防止只读环境报错）。
- 根据 `event['op']` 处理 `sync_calendar` 和 `sync_stock_list` 任务。

#### [NEW] [deploy_meta.py](file:///e:/gitee/microservice-stock/scf-collector/deploy_meta.py)
- 专门用于部署 `stock-scf-meta` 的脚本。
- **SDK 发布**: 使用 `TencentCloud SDK` 驱动 `UpdateFunctionCode`，实现自动化部署与容器刷新。

---

## Verification Plan

### Automated Tests
- **Unit Tests**: 编写 `tests/test_meta_sync.py`，使用 `pytest` 校验 Tushare 数据拉取和 DAO 存储逻辑（使用 Mock）。
- **Mock Run**: 在本地使用 `python meta_index.py` (模拟 event) 进行跑通校验。

### Manual Verification
- **Remote Invoke**: 使用 `models.InvokeRequest()` 编写远程触发脚本，验证云端真实环境下的执行状态（排除本地代理干扰）。
- **SQL Audit**: 执行 `SELECT COUNT(*) FROM trade_cal WHERE cal_date = CURDATE()` 校验同步结果。

---

## Readiness Check
- [x] **需求解析**: 剥离低频元数据任务至独立 SCF，按差异化频率同步（日历每月/股票列表每日）。
- [x] **依赖认证**: Tushare Token 已就绪；`meta_pipeline_run` 表已存在。
- [x] **角色激活**: [DB Auditor], [Backend Engineer], [Data Quality Steward], [Infra Specialist], [Requirement Architect], [Workflow Guard]
