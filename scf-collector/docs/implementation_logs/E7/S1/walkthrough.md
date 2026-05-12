# Walkthrough - E7-S1: 基础元数据云端同步 (Meta Foundation)

## 1. 实施概览

本任务完成了从旧 CVM 环境向腾讯云 Serverless (SCF) 环境的元数据迁移，确立了云端“真源”元数据同步体系。

### 核心变更
- **采集器扩展**: [tushare_cl.py](file:///e:/gitee/microservice-stock/scf-collector/shared/collectors/tushare_cl.py) 新增 `fetch_trading_calendar` 和 `fetch_stock_list`。
- **存储逻辑**: [dao.py](file:///e:/gitee/microservice-stock/scf-collector/shared/db/dao.py) 实现了 `trade_cal` 和 `stock_basic_info` 的 Upsert 逻辑，包含日期格式自动适配。
- **云端入口**: [meta_index.py](file:///e:/gitee/microservice-stock/scf-collector/meta_index.py) 实现了独立任务调度逻辑。
- **自动化部署**: [deploy_meta.py](file:///e:/gitee/microservice-stock/scf-collector/deploy_meta.py) 支持函数自动创建、VPC 配置及环境变量同步。

---

## 2. 验证证据 (Physical Evidence)

### 2.1 单元测试验证
通过 Mock Tushare API 验证了数据处理和日期转换逻辑的正确性。

```bash
python -m pytest tests/test_meta_sync.py
```

> **测试结果**:
> ```text
> tests\test_meta_sync.py ..                                               [100%]
> ============================== 2 passed in 7.55s ==============================
> ```

### 2.2 云端集成验证 (Remote Invoke)
使用 SDK 远程触发云端 `stock-scf-meta` 函数执行 `sync_calendar` 操作。

> **远程调用响应**:
> ```json
> {
>   "status": "success", 
>   "op": "sync_calendar", 
>   "count": 13162, 
>   "request_id": "22b7e6db-81dd-4e89-a58a-b28235a5b8f6"
> }
> ```

### 2.3 数据库真源审计 (True Source Audit)
在云端环境中执行 SQL 统计，确认数据已成功落库且符合预期。

| 审计项 | SQL 语句 | 真实结果 | 结论 |
| :--- | :--- | :--- | :--- |
| 交易日历总量 | `SELECT COUNT(*) FROM trade_cal` | **13,162** | PASS |
| 股票列表总量 | `SELECT COUNT(*) FROM stock_basic_info` | **5,834** | PASS |
| 任务流水审计 | `SELECT * FROM meta_pipeline_run LIMIT 1` | `Meta-Calendar | success` | PASS |

---

## 3. 验收标准 (AC) 覆盖情况

- [x] **AC1 (Calendar)**: 每日同步 Tushare 交易日历，更新 `trade_cal`。 (已验证落库 1.3w+ 条)
- [x] **AC2 (StockList)**: 同步全市场股票列表，更新 `stock_basic_info`。 (已验证落库 5800+ 条)
- [x] **AC3 (Isolation)**: 作为一个独立的 SCF (`stock-scf-meta`) 运行。 (已验证独立部署成功)

---

## 4. 交付清单
- [tushare_cl.py](file:///e:/gitee/microservice-stock/scf-collector/shared/collectors/tushare_cl.py)
- [dao.py](file:///e:/gitee/microservice-stock/scf-collector/shared/db/dao.py)
- [meta_index.py](file:///e:/gitee/microservice-stock/scf-collector/meta_index.py)
- [deploy_meta.py](file:///e:/gitee/microservice-stock/scf-collector/deploy_meta.py)
- [test_meta_sync.py](file:///e:/gitee/microservice-stock/scf-collector/tests/test_meta_sync.py)
