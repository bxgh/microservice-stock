# 数据管线字段映射矩阵 (Field Alignment Matrix)

本手册定义了 `scf-collector` 中各 ODS/Dim 表与上游数据源（以 Tushare 为主）的物理映射关系，作为数据质量审计（DQ Audit）的“真源”准则。

---

## 1. 交易日历表 (`trade_cal`)
- **数据源**: Tushare `trade_cal` 接口
- **主键**: `cal_date`, `exchange`

| MySQL 字段 | 原始 API 字段 | 类型转换 / 逻辑 | 示例 |
| :--- | :--- | :--- | :--- |
| `cal_date` | `cal_date` | `YYYYMMDD` -> `YYYY-MM-DD` | '2026-05-12' |
| `exchange` | `exchange` | 保持不变 (SSE/SZSE) | 'SSE' |
| `is_open` | `is_open` | `int` 保持不变 | 1 (开盘) / 0 (休市) |
| `pretrade_date` | `pretrade_date`| `YYYYMMDD` -> `YYYY-MM-DD` | '2026-05-11' |

---

## 2. 股票基础信息表 (`stock_basic_info`)
- **数据源**: Tushare `stock_basic` 接口
- **主键**: `ts_code`

| MySQL 字段 | 原始 API 字段 | 类型转换 / 逻辑 | 备注 |
| :--- | :--- | :--- | :--- |
| `ts_code` | `ts_code` | 保持不变 | e.g. '600519.SH' |
| `symbol` | `symbol` | 保持不变 | e.g. '600519' |
| `name` | `name` | 保持不变 | 股票简称 |
| `list_date` | `list_date` | `YYYYMMDD` -> `YYYY-MM-DD` | 上市日期 |
| `list_status` | `list_status` | 保持不变 | L(上市)/D(退市)/P(暂停) |
| `is_hs` | `is_hs` | 保持不变 | N(非沪深通)/H(沪股通)/S(深股通) |

---

## 3. 个股日线 K 线表 (`stock_kline_daily`)
- **数据源**: Tushare `daily` 接口 (P0) / AkShare `stock_zh_a_hist` (P1)
- **主键**: `ts_code`, `trade_date`

| MySQL 字段 | 原始 API 字段 | **关键转换逻辑** | 物理含义 |
| :--- | :--- | :--- | :--- |
| `ts_code` | `ts_code` | 保持不变 | 股票代码 |
| `trade_date` | `trade_date` | 归一化为 `YYYY-MM-DD` | 交易日期 |
| `open` / `close` | `open` / `close` | 保持不变 (Float) | 开盘/收盘价 |
| `pct_chg` | `pct_chg` | **/ 100.0** (百分比转小数) | 涨跌幅 (0.05 代表 5%) |
| `volume` | `vol` | 保持不变 (通常为“手”) | 成交量 |
| `amount` | `amount` | **× 1000.0** (千元转为元) | 成交额 (元) |

---

## 4. 系统审计与就绪表 (Meta 层)
- **数据源**: 系统内部生成 (System Generated)

| 表名 | 关键字段 | 逻辑来源 |
| :--- | :--- | :--- |
| `meta_pipeline_run` | `run_id` | 取自 SCF `context.request_id` (UUID) |
| `meta_pipeline_run` | `status` | `success` 或 `error` |
| `meta_data_readiness`| `status` | 采集入库成功后固定为 `READY` |

---

## 5. 维护规范
1. **禁止直接修改 ODS 层单位**: 所有单位换算（如 amount 乘以 1000）必须在 Python 采集器的 `normalize_data` 方法中完成。
2. **单位红线**: `amount` 全库统一单位为 **“元”**，`pct_chg` 全库统一单位为 **“小数”**。
