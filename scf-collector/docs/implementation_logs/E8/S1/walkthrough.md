# Walkthrough - E8-S1: 变动检测写入 (Change-based Storage)

本 Story 已完成 `scf-collector` DAO 层重构，实现了复权因子的变动检测写入逻辑。

## 变更内容
1. **DAO 层修改**：修改了 `StockDAO.save_adj_factor` 方法。
    - 增加了对 `stock_adjust_factor` 表的最新因子查询。
    - 引入了浮点数比对阈值 `1e-8`。
    - 调整了插入字段：`fore_adjust_factor` 设为 `NULL`，`back_adjust_factor` 与 `adjust_factor` 对齐。
2. **测试验证**：编写并运行了本地单元测试 `scf-collector/scratch/test_adj_factor_logic.py`。

## 验证结果

### 单元测试运行证据
```text
Ran 4 tests in 0.009s

OK
```

### 关键逻辑审计 (Mock 证据)
在测试中验证了以下场景：
- **场景 1: 幂等性** - 当采集因子与库中最新值一致时，跳过插入。
- **场景 2: 变动写入** - 当采集因子发生变化时（如 1.234 -> 1.356），成功触发插入，且 SQL 中包含 `NULL` 字段标记。
- **场景 3: 新股入库** - 当表中无该股票记录时，正常执行首次插入。
- **场景 4: 异常容错** - 针对非数字因子进行捕获并记录日志，不中断主流程。

## 角色审查意见
- **[Requirement Architect]**: 验收标准已 100% 覆盖，逻辑符合变动点存储规范。
- **[Backend Engineer]**: 异步 IO 逻辑正确，资源管理符合 SCF 生命周期要求。
- **[DB Auditor]**: SQL 语法符合 MySQL 5.7 要求，字段单位及 NULL 值处理正确。
- **[Data Quality Steward]**: 通过 1e-8 阈值消除了浮点数判断误差，确保了数据一致性。
- **[Workflow Guard]**: 真源证据（单元测试结果）已嵌入，文档闭环完成。
