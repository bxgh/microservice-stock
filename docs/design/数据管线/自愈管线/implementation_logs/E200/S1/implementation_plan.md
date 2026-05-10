# Implementation Plan - E200-S1: 差异化跨源扫描器

## 1. 需求解析
核心逻辑：通过 `mootdx-api` 获取实时/历史数据，与 `tushare-api` 及 `akshare-api` 数据进行字段级对齐。采用“取二一致”算法判定数据准确性，并对异常字段生成修复建议记录。

## 2. 依赖认证
- [x] **数据源**: `tushare-api` (Port 8005), `mootdx-api` (Port 8007), `akshare-api` (Port 8003)。
- [x] **表结构**: `stock_kline_daily` (ODS), `dq_findings` (治理表)。
- [x] **角色激活**: 
  - [Requirement Architect] (方案架构与 AC 设计)
  - [Backend Engineer] (异步 IO 与并发安全)
  - [Data Quality Steward] (校验矩阵与数据口径)
  - [DB Auditor] (审计表写入规范)
  - [Infra Specialist] (服务通信与熔断重试)
  - [QA/Test Engineer] (集成测试验证)
  - [Workflow Guard] (流程存证与 Git 规范)

## 3. 拟动文件 [MODIFY]
1. `stock-manager-api/app/services/cross_compare_service.py`: 核心仲裁逻辑重构。
2. `stock-manager-api/app/utils/http_client.py`: 增加 `mootdx` 服务映射。

## 4. 拟动文件 [NEW]
1. `tests/integration/test_e200_s1_arbitration.py`: 跨源仲裁集成测试用例。

## 5. 验证计划
- **自动化测试**: 运行 `pytest tests/integration/test_e200_s1_arbitration.py`，模拟三源数据冲突场景。
- **物理查验**: 检查 `dq_findings` 表是否正确记录了仲裁过程中的异常源信息。
