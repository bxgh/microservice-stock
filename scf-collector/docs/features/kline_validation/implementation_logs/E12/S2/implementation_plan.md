# E12-S2 实施计划：影子源随机对账与物理校验

本 Story 旨在建立 Tushare 数据与 AkShare 数据之间的影子对账机制，确保 K 线价格的真实性和准确性。

## 用户审核

> [!TIP]
> **采样策略**：考虑到 API 额度，我们将默认采样率设定为 1%（每日约 50 只股票）。对于波动剧烈（如涨跌停）的股票，采样权重会适当增加。

## 待办任务

### [E5] 影子验证体系开发

#### [NEW] [shadow_validator.py](file:///home/ubuntu/microservice-stock/scf-collector/scripts/shadow_validator.py)
核心对账逻辑：
- 随机采样算法：每日抽取 1% 样本。
- 双源对账：本地 (Tushare) vs AkShare。
- 物理校验：执行 `low <= high`, `pct_chg` 精度校验。
- 异常标记：写入 `meta_task_queue`。

#### [NEW] [internal_consistency_checker.py](file:///home/ubuntu/microservice-stock/scf-collector/scripts/internal_consistency_checker.py)
库内静态审计：
- 检查 `amount / volume` 的量价合理性。
- 检查是否存在 `open = 0` 等无效记录。

## 验证计划

### 对账实验
- 故意篡改库中一条记录的价格，运行 `shadow_validator.py`，确认其能精准识别出 `PRICE_MISMATCH`。

### 报告集成
- 将校验结果（对账成功率、异常分布）整合进每日 `REPORT.html`。
