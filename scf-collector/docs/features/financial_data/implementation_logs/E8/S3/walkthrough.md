# Walkthrough - E8-S3: 历史数据字段回填 (Historical Data Backfill)

本 Story 完成了对 `stock_adjust_factor` 存量数据的字段对齐修复。

## 变更内容
1. **数据修复 (T1)**：
    - 通过分批 `UPDATE` 语句，将所有 `back_adjust_factor IS NULL` 的历史记录对齐到了 `adjust_factor` 值。
2. **质量验证 (T2)**：
    - 经用户执行审计 SQL 确认，全库已不存在 `back_adjust_factor` 缺失且 `adjust_factor` 存在的异常行。

## 验证证据
- **审计 SQL**: `SELECT COUNT(*) FROM stock_adjust_factor WHERE back_adjust_factor IS NULL AND adjust_factor IS NOT NULL;`
- **结果**: `0`

## 角色审查意见
- **[Data Quality Steward]**: 存量数据字段一致性已达成，满足下游 ADS 层直接引用 `back_adjust_factor` 的前置条件。
- **[Workflow Guard]**: 遵循“先备份/分批执行 -> 后审计”的稳健操作流程。
