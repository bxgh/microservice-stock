
# 指数与ETF数据补全实施方案

## 1. 目标
补全历史K线数据，并确保后续每日采集任务包含以下标的：
- **指数 (Indices)**: 上证指数、深证成指、创业板指、科创50等主流指数。
- **ETF (Exchange Traded Funds)**: 全市场股票型、债券型、商品型等ETF基金。

## 2. 现状分析
- **原有机制**: `baostock-api` 负责全市场日线同步，但仅覆盖 A 股股票 (sh.6/sz.0/sz.3/sh.688/bj.)。
- **数据源评估**:
  - **Baostock**: 支持指数数据 (`sh.000...`, `sz.399...`)，但无法获取 ETF 数据 (测试返回空)。
  - **AkShare**: 支持全市场 ETF 数据接口 (`fund_etf_hist_em`)。

## 3. 实施策略

### 3.1 指数 (Indices) - 已实施
- **方案**: 直接复用 `baostock-api` 的现有链路。
- **修改点**: 修改 `BaoStockService.get_all_a_shares` 方法，增加指数前缀过滤：
  - `sh.000...` (上证指数系列)
  - `sz.399...` (深证指数系列)
- **回溯逻辑**:
  - 代码变更后，`sync_daily_increment` 任务会自动识别数据库中缺失的指数代码。
  - 自动触发历史数据回补 (默认回溯至 1990-12-19)。
- **存储**: 存入 `stock_kline_daily` 表，代码格式保持为 `sh.000001`, `sz.399001` 等。

### 3.2 ETF - 待实施 (AkShare路径)
由于 Baostock 不支持 ETF，需在 `akshare-api` 服务中新增采集能力。

#### 3.2.1 基础设施升级
- **数据库连接**: 为 `akshare-api` 服务添加 MySQL 连接能力 (`app/utils/database.py`)。
- **依赖库**: 确保环境包含 `aiomysql` 或 `asyncmy` (与 `baostock-api` 保持一致)。

#### 3.2.2 新增 ETF 服务 (`EtfService`)
- **获取列表**: 使用 `ak.fund_etf_spot_em()` 获取全市场 ETF 列表。
- **获取K线**: 使用 `ak.fund_etf_hist_em(symbol=code, period="daily", ...)` 获取日线数据。
- **数据清洗**: 统一格式为 `stock_kline_daily` 表结构。
  - `code`: 格式化为 `sh.51xxxx` 或 `sz.15xxxx`。
  - `trade_status`: 默认为 1 (交易中)。
  - `pre_close`, `amount`, `turnover` 等字段需进行映射。

#### 3.2.3 调度任务
- 新增 `daily_etf_sync_job` 定时任务 (建议 17:30 后执行)。
- 首次运行时自动全量回溯。

## 4. 执行步骤
1. [x] 修改 `baostock-api` 代码以支持指数。
2. [ ] 为 `akshare-api` 添加数据库支持。
3. [ ] 实现 `EtfService` 及 ETF 同步逻辑。
4. [ ] 注册定时任务并手动触发一次全量回溯。
5. [ ] 验证数据完整性。

## 5. 验证方法
- 查询数据库：
```sql
-- 验证指数
SELECT COUNT(*) FROM stock_kline_daily WHERE code LIKE 'sh.000%' OR code LIKE 'sz.399%';
-- 验证 ETF
SELECT COUNT(*) FROM stock_kline_daily WHERE code LIKE 'sh.51%' OR code LIKE 'sz.15%';
```
