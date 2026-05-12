# E7 数据管线 MySQL 数据库论证报告 (V2 - 真源对齐版)

> **基准文档**: `docs/design/复盘/db_inventory.md` (2026-05-05)
> **原则**: 严格遵守物理表结构，禁止任何 DDL 变更，逻辑层进行类型适配。

---

## 1. 核心维表逻辑对齐 (E7-S1)

### 1.1 交易日历表 (`trade_cal`)
- **物理定义** (根据 `db_inventory.md` L2279):
    - `cal_date`: DATE (Primary Key)
    - `exchange`: VARCHAR(50)
    - `is_open`: INT(11)
    - `pretrade_date`: DATE
- **适配逻辑**: 
    - Tushare API 返回的 `YYYYMMDD` 字符串必须转换为 Python `datetime.date` 对象。
    - `is_open` 字符串 ('0'/'1') 必须显式转换为 `INT`。
- **操作策略**: 使用 `INSERT INTO ... ON DUPLICATE KEY UPDATE`。

### 1.2 股票基础信息表 (`stock_basic_info`)
- **物理定义** (根据 `db_inventory.md` L1828):
    - `ts_code`: VARCHAR(20) (Primary Key)
    - `list_date`: DATE
    - `delist_date`: DATE
    - `is_hs`: VARCHAR(1)
    - (共计 19 个字段，含 `industry`, `market`, `act_name` 等)
- **适配逻辑**:
    - 确认为本项目最全的股票维表 (5,928 行)。
    - 同步时需严格映射 Tushare `stock_basic` 的 19 个对应字段。
    - 针对 `DATE` 类型字段进行预处理，防止空字符串或格式错误导致写入失败。

---

## 2. 结论与约束
实施 E7-S1 时，`StockDAO` 必须以 `db_inventory.md` 中的字段名和物理类型为唯一准则。
禁止在 SCF 代码中使用 `to_sql(if_exists='replace')`，必须保持 DDL 稳定性。
