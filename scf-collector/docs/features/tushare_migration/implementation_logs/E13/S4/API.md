# E13-S4 内部数据接口设计 (Internal API Reference)

本 Story 为纯后台数据迁移与就绪探测模块，不直接对外暴露公共 HTTP 路由。核心交互接口为 `StockDAO` 类中的 4 个高并发异步批量物理写入方法。

---

## 1. 资产负债表持久化接口

### 方法签名
```python
@classmethod
async def save_balancesheet(cls, data: List[Dict[str, Any]]) -> int:
```

### 功能描述
幂等保存资产负债表原始明细。内部调用 `_clean_nan` 清理 pandas 转换带来的浮点数空值，对公告期唯一键执行 `ON DUPLICATE KEY UPDATE` 动态覆盖，以支持上市公司更正报表。

### 数据映射结构
| Tushare 原生字段 | 数据库物理字段 | 数据类型 | 说明 |
|---|---|---|---|
| `ts_code` | `ts_code` | `VARCHAR(12)` | 股票代码 (唯一索引主键部分) |
| `ann_date` | `ann_date` | `DATE` | 公告日期 |
| `f_ann_date` | `f_ann_date` | `DATE` | 实际公告日期 |
| `end_date` | `end_date` | `DATE` | 报告期结束日期 (唯一索引主键部分) |
| `report_type` | `report_type` | `VARCHAR(10)` | 报表类型 (唯一索引主键部分) |
| `comp_type` | `comp_type` | `VARCHAR(10)` | 公司类型 (1一般工商业 2银行 3证券 4保险) |
| `total_assets` | `total_assets` | `DECIMAL(20,4)` | 资产总计 (元) |
| `total_liab` | `total_liabilities` | `DECIMAL(20,4)` | 负债合计 (元) |
| `st_borr` | `short_term_borrow` | `DECIMAL(20,4)` | 短期借款 (元) |
| `lt_borr` | `long_term_borrow` | `DECIMAL(20,4)` | 长期借款 (元) |

---

## 2. 利润表持久化接口

### 方法签名
```python
@classmethod
async def save_income(cls, data: List[Dict[str, Any]]) -> int:
```

### 功能描述
批量幂等保存利润表数据。

### 数据映射结构
| Tushare 原生字段 | 数据库物理字段 | 数据类型 | 说明 |
|---|---|---|---|
| `ts_code` | `ts_code` | `VARCHAR(12)` | 股票代码 (唯一索引主键部分) |
| `end_date` | `end_date` | `DATE` | 报告期结束日期 (唯一索引主键部分) |
| `report_type` | `report_type` | `VARCHAR(10)` | 报表类型 (唯一索引主键部分) |
| `n_income` | `net_profit` | `DECIMAL(20,4)` | 净利润 (元) |
| `total_revenue` | `total_revenue` | `DECIMAL(20,4)` | 营业总收入 (元) |
| `revenue` | `revenue` | `DECIMAL(20,4)` | 营业收入 (元) |

---

## 3. 现金流量表持久化接口

### 方法签名
```python
@classmethod
async def save_cashflow(cls, data: List[Dict[str, Any]]) -> int:
```

### 功能描述
批量幂等保存现金流量表数据。

### 数据映射结构
| Tushare 原生字段 | 数据库物理字段 | 数据类型 | 说明 |
|---|---|---|---|
| `ts_code` | `ts_code` | `VARCHAR(12)` | 股票代码 (唯一索引主键部分) |
| `end_date` | `end_date` | `DATE` | 报告期结束日期 (唯一索引主键部分) |
| `report_type` | `report_type` | `VARCHAR(10)` | 报表类型 (唯一索引主键部分) |
| `n_cashflow_act` | `net_cash_flows_oper_act` | `DECIMAL(20,4)` | 经营活动产生的现金流量净额 (元) |
| `n_cashflow_inv_act` | `net_cash_flows_inv_act` | `DECIMAL(20,4)` | 投资活动产生的现金流量净额 (元) |
| `n_cash_flows_fnc_act` | `net_cash_flows_fnc_act` | `DECIMAL(20,4)` | 筹资活动产生的现金流量净额 (元) |

---

## 4. 财务指标与关键比率持久化接口

### 方法签名
```python
@classmethod
async def save_fina_indicator(cls, data: List[Dict[str, Any]]) -> int:
```

### 功能描述
批量幂等保存财务关键指标与比率。**关键处理契约**：所有表达比例与百分比的列（如 `roe`, `grossprofit_margin`, `debt_to_assets` 等），入库前自动除以 `100.0` 换算为标准小数存储，同时使用 `round(val, 4)` 保留 4 位小数避免截断警告。

### 数据映射结构
| Tushare 原生字段 | 数据库物理字段 | 数据类型 | 转换契约 | 说明 |
|---|---|---|---|---|
| `ts_code` | `ts_code` | `VARCHAR(12)` | 无转换 | 股票代码 (唯一索引部分) |
| `end_date` | `end_date` | `DATE` | 无转换 | 报告期结束日期 (唯一索引部分) |
| `roe` | `roe` | `DECIMAL(10,4)` | `float(val) / 100.0` | 净资产收益率 (标准小数) |
| `roe_dt` | `roe_dt` | `DECIMAL(10,4)` | `float(val) / 100.0` | 扣除非经常损益后的 ROE (标准小数) |
| `roa` | `roa` | `DECIMAL(10,4)` | `float(val) / 100.0` | 总资产收益率 (标准小数) |
| `netprofit_margin` | `netprofit_margin` | `DECIMAL(10,4)` | `float(val) / 100.0` | 销售净利率 (标准小数) |
| `grossprofit_margin`| `grossprofit_margin` | `DECIMAL(10,4)` | `float(val) / 100.0` | 销售毛利率 (标准小数) |
| `debt_to_assets` | `debt_to_assets` | `DECIMAL(10,4)` | `float(val) / 100.0` | 资产负债率 (标准小数) |
| `current_ratio` | `current_ratio` | `DECIMAL(10,4)` | 无转换 | 流动比率 (倍数) |
| `quick_ratio` | `quick_ratio` | `DECIMAL(10,4)` | 无转换 | 速动比率 (倍数) |
