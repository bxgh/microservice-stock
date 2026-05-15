# Implementation Plan - E8-S3: 历史数据字段回填 (Historical Data Backfill)

本 Story 旨在修复 `stock_adjust_factor` 表中历史数据的字段缺失，确保 `back_adjust_factor` 与 `adjust_factor` 逻辑对齐。

## 需求解析
- **核心逻辑**：针对存量数据中 `back_adjust_factor` 为 NULL 的记录，将其值更新为同行的 `adjust_factor`。
- **背景**：在 S1 重构后，新入库数据已实现自动对齐，本项目负责清理历史遗留的 NULL 值。

## 依赖认证
- **数据表**：`stock_adjust_factor` (MySQL 5.7)。
- **操作权限**：具备 `UPDATE` 权限。

## 方案设计
### 1. 分批回填
使用 `LIMIT 10000` 分批执行 UPDATE，避免长事务锁表及对主从同步造成压力。
### 2. 验证
通过 `COUNT(*) WHERE ... IS NULL` 确保回填彻底。

## 任务列表 (Tasks)
- [x] **E8-S3-T1**: 执行分批回填 SQL (User 执行)
- [x] **E8-S3-T2**: 验证回填结果 (User 验证)
