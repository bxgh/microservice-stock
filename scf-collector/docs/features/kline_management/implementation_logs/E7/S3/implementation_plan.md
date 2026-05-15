# E7-S3: 字段完整性契约强制 (Data Contract)

## 1. 业务背景
为了确保不同数据源（Tushare/AkShare）返回的数据进入 `ods` 层前具备一致的格式和量纲，需要建立强类型的字段契约。这包括：
- 统一股票代码格式（如 `600519.SH`）。
- 统一成交量单位（手）和成交额单位（元）。
- 确保关键字段（如 `pre_close`）在缺失时可被反推补齐。
- 过滤无效数据（如停牌导致的零成交）。

## 2. 核心目标
- [ ] **E7-S3-T1**: 迁移并统一定义 `KLineModel` 至 `shared/collectors/base.py`。
- [ ] **E7-S3-T2**: 完善 `AkShareAdapter`：
    - 确保 `stock_zh_a_spot_em` 字段映射准确。
    - 转换成交量：股 -> 手。
    - 统一代码后缀。
- [ ] **E7-S3-T3**: 实现停牌清洗逻辑：`vol == 0` 或 `ohl == 0` 时过滤。
- [ ] **E7-S3-T4**: 实现字段合成器：若 `pre_close` 缺失，使用 `close / (1 + pct_chg)` 补齐。

## 3. 拟议变更

### [Component] shared/collectors/base.py
- [MODIFY] 迁移 `KLineModel` 定义。
- [MODIFY] 修改 `BaseCollector.fetch_daily_kline` 返回类型为 `List[KLineModel]`。

### [Component] shared/collectors/akshare_adapter.py
- [MODIFY] 重构 `from_em_spot_records`：
    - 加入 `pre_close` 补全逻辑。
    - 加入更严格的停牌/无效数据清洗。
    - 确保成交量单位转换正确（股 -> 手）。

### [Component] shared/collectors/tushare_cl.py
- [MODIFY] 更新返回类型为 `List[KLineModel]`。

### [Component] shared/utils/models.py
- [DELETE] 移除冗余的 `KLineModel`（已迁移至 `base.py`）。

## 4. 验证计划

### 自动化测试
- [NEW] `tests/test_akshare_contract.py`: 验证 Adapter 的量纲转换、代码重构、停牌过滤及字段合成逻辑。
- 验证 `TushareCollector` 和 `AkShareCollector` 的返回结果符合 `KLineModel` 契约。

### 手动验证
- 通过日志确认采集过程中 `Skipped (Suspended)` 的记录。
