# E7-S3 实施验收文档 (Walkthrough)

## 1. 实施概览
本 Story 完成了采集链路的"字段契约化"改造。通过在 `BaseCollector` 层强制要求返回 `KLineModel`，并配套升级了 `AkShareAdapter` 的清洗与合成逻辑，确保了数据源的归一化。

## 2. 核心改动展示

### 2.1 字段合成器 (Field Synthesizer)
在 `AkShareAdapter` 中，针对昨收价缺失的情况实现了自动补齐：
```python
# shared/collectors/akshare_adapter.py
if pre_close == 0 and pct_chg_val != -1:
    pre_close = round(close_price / (1 + pct_chg_val), 3)
```

### 2.2 停牌清洗逻辑 (Cleaner)
实现了更严格的 EM 源停牌过滤：
```python
# 若成交量为 0 且 (开盘/最高/最低任一为 0)，判定为停牌
if vol_raw == 0 and (open_price == 0 or high_price == 0 or low_price == 0):
    logger.debug(f"Skipped {ts_code} (Suspended/Invalid)")
    continue
```

### 2.3 契约强制执行
`BaseCollector` 接口现在强制返回模型，且 `StockDAO` 完美适配：
```python
# shared/db/dao.py
for item in data:
    params = item.model_dump() if hasattr(item, 'model_dump') else item
    res = await execute_query(sql, params, is_select=False)
```

## 3. 验证结果

### 自动化验证
- **代码完整性**: 修复了 `akshare_cl.py` 中因重构导致的 `import` 缺失及类型标注错误。
- **量纲对齐**: 
    - AkShare: `volume` (股 -> 手), `pct_chg` (% -> 小数)。
    - Tushare: `amount` (千元 -> 元), `pct_chg` (% -> 小数)。

### 质量审计
- 运行 `functions/daily_quotes/index.py` 的 `verify` 模式，确认不同源返回的 `KLineModel` 属性可被正常访问。

## 4. 交付清单
- [x] 核心代码修改: `base.py`, `akshare_adapter.py`, `akshare_cl.py`, `tushare_cl.py`, `dao.py`
- [x] 实施日志: `docs/implementation_logs/E7/S3/` (含 Plan, Task, Report, API, Walkthrough)
- [x] 进度更新: `docs/E7_Reliability_Validation.md` (已标记完成)
