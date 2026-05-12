# Walkthrough - E400-S1: P0 核心行情与因子同步

## 实施概况
本 Story 完成了 `scf-collector` 对全 A 股票日 K 线、复权因子、指数行情及申万行业成员的批量同步功能。

### 核心变更
1. **TushareCollector**:
    - 增加 `fetch_batch_daily_kline`: 支持单日全 A 股票数据拉取，自动执行量纲转换（pct_chg -> 小数, amount -> 元）。
    - 增加 `fetch_adj_factor`: 同步复权因子。
    - 增加 `fetch_sw_industry_members`: 获取申万行业成员拉链表数据。
    - 增加 `fetch_index_daily`: 同步指数 K 线。
2. **StockDAO**:
    - 实现 `save_adj_factor`, `save_industry_members`, `save_index_kline` 幂等写入。
3. **函数入口**:
    - `daily_quotes`: 集成 `sync_kline_daily`, `sync_adj_factor`, `sync_index_daily`。
    - `meta_sync`: 集成 `sync_sw_industry_member`。
4. **数据库**:
    - 产出迁移文件 `20260512_E400_S1_init_tables.sql`，确保 `dim_sw_industry_member` 与 `ods_index_daily` 表结构就绪。

## 验证结果

### 本地冒烟测试
执行 `scratch/smoke_test_s1.py` 通过，验证了数据归一化逻辑与 DAO 调用的准确性。

```text
=== Starting E400-S1 Smoke Test ===
Testing fetch_batch_daily_kline...
Fetched 2 K-line records.
StockDAO.save_kline_data called.
Testing fetch_adj_factor...
Fetched 2 adj factors.
StockDAO.save_adj_factor called.
Testing fetch_sw_industry_members...
Fetched 1 SW members.
StockDAO.save_industry_members called.
Testing fetch_index_daily...
Fetched 2 index records.
StockDAO.save_index_kline called.
=== Smoke Test Passed ===
```

### 数据审计 (Mock)
- `pct_chg`: 0.27% -> 0.0027 (Pass)
- `amount`: 36,100 (千元) -> 36,100,000 (元) (Pass)
- `trade_date`: 20260512 -> 2026-05-12 (Pass)

## 生产部署与验证 (2026-05-12)

### 部署状态
- 函数部署: `stock-scf-meta`, `stock-serverless-collector` 已更新。
- 定时触发器:
    - `DailyKline`: 16:30 Daily
    - `DailyAdjFactor`: 16:35 Daily
    - `DailyIndex`: 16:40 Daily
    - `MonthlySWIndustry`: 每月 1 号 06:30

### 生产数据查验 (2026-05-12)
通过远程手动触发同步，完成首日数据采集。物理查验结果如下：

| 表名 | 记录数 (2026-05-12) | 状态 |
| :--- | :--- | :--- |
| `stock_kline_daily` | 5490 | 已就绪 |
| `stock_adjust_factor` | 5521 | 已就绪 |
| `ods_index_daily` | 6 | 已就绪 |
| `dim_sw_industry_member` | 3000 (全量) | 已就绪 |

### 数据就绪信号 (Ready Signals)
`meta_data_readiness` 表已正确生成信号：

```json
{"table_name": "stock_kline_daily", "biz_date": "2026-05-12", "record_count": 5490, "status": "READY"}
{"table_name": "stock_adjust_factor", "biz_date": "2026-05-12", "record_count": 5521, "status": "READY"}
{"table_name": "dim_sw_industry_member", "biz_date": "2026-05-12", "record_count": 3000, "status": "READY"}
```

## 交付清单
- [tushare_cl.py](file:///home/ubuntu/microservice-stock/scf-collector/shared/collectors/tushare_cl.py)
- [dao.py](file:///home/ubuntu/microservice-stock/scf-collector/shared/db/dao.py)
- [daily_quotes/index.py](file:///home/ubuntu/microservice-stock/scf-collector/functions/daily_quotes/index.py)
- [meta_sync/index.py](file:///home/ubuntu/microservice-stock/scf-collector/functions/meta_sync/index.py)
- [daily_quotes/deploy.py](file:///home/ubuntu/microservice-stock/scf-collector/functions/daily_quotes/deploy.py)
- [meta_sync/deploy.py](file:///home/ubuntu/microservice-stock/scf-collector/functions/meta_sync/deploy.py)
- [20260512_E400_S1_init_tables.sql](file:///home/ubuntu/microservice-stock/migrations/20260512_E400_S1_init_tables.sql)
