# SQL 占位符格式化与空值转换踩坑记录 (String Placeholder & NoneType Conversion)

在执行 Epic E15 的 11 年（2015-01-01 至今）盘后历史数据全量回填时，我们遇到了两个具有共性的数据库与数据转换底层设计踩坑。本文记录这些技术痛点、排查细节及最终修复对策。

---

## 踩坑 1: SQL 字符串格式化中的单百分号 `%` 报错

### 1. 踩坑记录 (The Pitfall)
在派生行情广度 `derive_market_breadth` 时，Python 报告如下错误：
```
TypeError: not enough arguments for format string
```
此错误发生在 `execute_query(sql_agg, (target_date,), is_select=True)` 执行时，底层的 Python 字符串格式化无法通过。

### 2. 原因剖析与对比 (Options Explored)
*   **分析**：在 SQL 语句中，我们使用了 `ts_code NOT LIKE '900%' AND ts_code NOT LIKE '200%'` 来过滤 B 股代码。
*   **痛点**：当使用 `aiomysql` 或 `PyMySQL` 并配合元组/字典参数化查询时，数据库驱动会在底层使用 `%` 进行字符串格式化。此时，SQL 语句中的 literal 百分号 `%` (如 `'900%'`) 会被误判为占位符占位，导致解析时报“参数不足”的错误。
*   **解决方案选择**：
    *   *方案 A*：在 SQL 拼接前用 Python 先格式化。❌ 会引入 SQL 注入风险，破坏参数化查询的安全门禁。
    *   *方案 B*：将通配符化为参数传入，如 `NOT LIKE %s`，并在参数元组中传入 `'900%'`。  这可行，但对静态过滤而言，让代码变得十分繁琐。
    *   *方案 C (择优决策)*：**双百分号转义**。将 SQL 内部的单百分号改为 `%%`（例如 `NOT LIKE '900%%'`），以此向 Python 格式化引擎显式声明这是转义后的普通字符 `%`。

### 3. 择优决策 (Optimal Choice)
选择 **方案 C (双百分号转义)**，这是最干净、对 SQL 结构破坏最小的方案。

```diff
- AND ts_code NOT LIKE '900%' AND ts_code NOT LIKE '200%'
+ AND ts_code NOT LIKE '900%%' AND ts_code NOT LIKE '200%%'
```

---

## 踩坑 2: 久远历史数据中 `NoneType` 强转 `float` 导致的崩溃

### 1. 踩坑记录 (The Pitfall)
在解决百分号格式化后，再次运行回填时，对 2015-01-05 执行 `derive_market_breadth` 触发了如下错误：
```
TypeError: float() argument must be a string or a real number, not 'NoneType'
```
该错误发生于提取复权因子 `back_adjust_factor` 或行情收盘价 `close` 并转换为 `float` 时。

### 2. 原因剖析与对比 (Options Explored)
*   **分析**：早期（如 2015 年）的某些股票，由于处于停牌状态、刚上市或者历史数据缺失，其 `back_adjust_factor`（复权因子）或 `close`（收盘价）在数据库中物理存在 `NULL` 值。
*   **痛点**：老代码中直接使用了 `float(r['back_adjust_factor'])` 或 `float(r['close'])`，在面对 `None` 时直接崩溃，中止了当日数据的进一步计算派生。
*   **解决方案选择**：
    *   *方案 A*：直接在 SQL 中加 `COALESCE` 过滤。❌ 如果遇到没有复权因子的股票，直接赋予 1.0，但对多字段处理较繁琐。
    *   *方案 B (择优决策)*：在 Python 数据提取侧加入 **安全守卫判断**，若字段为 `None` 则自动赋予合理的业务默认值（复权因子默认为 `1.0`，收盘价默认为 `0.0`）。

### 3. 择优决策 (Optimal Choice)
选择 **方案 B**，在提取端拦截 `None`：
```python
f_factor_val = float(f_factor) if f_factor is not None else 1.0
close_val = float(r['close']) if r['close'] is not None else 0.0
```

---

## 复用技巧与最佳实践 (Reusable Tips)

1.  **SQL LIKE 过滤规范**：凡是在 Python 异步/同步参数化查询 SQL 语句中编写含通配符的 `LIKE` 语句，一律强制将单百分号 `%` 改写为双百分号 `%%` 转义，规避格式化异常。
2.  **弹性数据加载规范**：从底层物理表（特别是含有 `ods_` 或 `dwd_` 前缀的原始/明细历史数据表）加载浮点数时，**必须前置防空（NoneType）校验**，禁止盲目信任库表的 `NOT NULL` 属性。
