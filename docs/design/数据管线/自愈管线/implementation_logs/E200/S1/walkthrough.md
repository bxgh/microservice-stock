# Walkthrough - E200-S1: 差异化跨源扫描器

## 1. 实施概览
本任务实现了 A 股自愈型数据管线的核心扫描组件——差异化跨源扫描器。
- **集成源**: 引入 `mootdx-api` 作为新的 K 线数据源。
- **仲裁逻辑**: 实现了“取二一致”的三源仲裁引擎（Tushare/ODS, Mootdx, AkShare）。
- **自动化校验**: 支持 OHLCV 字段级比对，并根据差异严重程度分类记录至 `dq_findings` 表。

## 2. 变更详情
### 2.1 基础设施集成
- [MODIFY] `docker-compose.yml`: 为 `stock-manager` 服务增加 `MOOTDX_API_URL` 环境变量。
- [MODIFY] `stock-manager-api/app/config.py`: 增加 `MOOTDX_API_URL` 配置项。
- [MODIFY] `stock-manager-api/app/utils/http_client.py`: 建立 `mootdx` 服务路由映射。

### 2.2 业务逻辑重构
- [MODIFY] `stock-manager-api/app/services/cross_compare_service.py`:
  - 移除已废弃的 `BaoStock` 获取逻辑。
  - 实现 `_fetch_from_mootdx` 异步抓取并自动对齐 ODS 字段（含成交量单位换算）。
  - 实现 `_arbitrate_triple` 仲裁引擎，支持 5 种比对场景（全一致、主从不一、ODS 异常、全不一致、降级双源）。

## 3. 验证结果
### 3.1 自动化测试
运行 `pytest /app/test_e200_s1_arbitration.py`，3 个核心测试用例全部通过。
```text
test_e200_s1_arbitration.py::test_arbitrate_triple_majority_win PASSED
test_e200_s1_arbitration.py::test_arbitrate_triple_ods_error PASSED
test_e200_s1_arbitration.py::test_arbitrate_timeout_degrade PASSED
```

### 3.2 物理查验 (True Source)
对 `600519.SH` (2026-05-08) 执行真实比对：
- **场景**: ODS 与 Mootdx 数据完全一致（经单位换算后），AkShare 接口返回 404（自动触发降级逻辑）。
- **结果**: `Result: None` (表示未发现异常)，符合预期。

## 4. 存证记录
- **测试文件**: `tests/integration/test_e200_s1_arbitration.py`
- **关键日志**:
```json
{"severity": "WARN", "description": "跨源比对: 外部单源与主源不一致. (由于缺少仲裁源，无法判定胜负)"}
```
*(注：以上日志为模拟异常场景时产生，正常匹配时不记录)*
