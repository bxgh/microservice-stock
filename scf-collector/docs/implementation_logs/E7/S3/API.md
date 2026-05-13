# E7-S3 接口变更文档

## 1. 基础架构变更

### `shared.collectors.base.BaseCollector`
- **变更**: `fetch_daily_kline` 返回类型变更。
- **旧接口**: `async def fetch_daily_kline(...) -> List[Dict[str, Any]]`
- **新接口**: `async def fetch_daily_kline(...) -> List[KLineModel]`

## 2. 数据契约定义

### `shared.utils.models.KLineModel`
所有采集器必须返回该模型实例，其核心字段定义如下：

| 字段 | 类型 | 说明 | 单位/量纲 |
| :--- | :--- | :--- | :--- |
| `ts_code` | `str` | 标准代码 | `600519.SH` |
| `trade_date`| `str` | 交易日期 | `YYYY-MM-DD` |
| `open` | `float` | 开盘价 | 元 |
| `close` | `float` | 收盘价 | 元 |
| `pre_close` | `float` | 昨收价 | 元 (支持反推补齐) |
| `pct_chg` | `float` | 涨跌幅 | **小数** (0.05 = 5%) |
| `volume` | `float` | 成交量 | **手** |
| `amount` | `float` | 成交额 | **元** |

## 3. 内部方法增强

### `AkShareAdapter.from_em_spot_records`
- **逻辑**: 增加字段合成与数据清洗功能。
- **副作用**: 过滤掉停牌数据，不会在返回列表中出现。

## 4. 调用建议
下游业务逻辑应优先使用 `.attribute` 访问字段（如 `item.close`），虽然模型仍支持 `.get()` 或 `[]` 访问（如果转换为 dict）。
