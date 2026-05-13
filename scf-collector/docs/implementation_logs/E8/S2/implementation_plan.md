# Implementation Plan - E8-S2: 字段废弃标记 (Deprecated Field Marking)

本项目旨在通过数据库 Schema 注释和全局文档明确标记 `fore_adjust_factor` 为废弃字段，引导下游开发转向动态前复权计算。

## 需求解析
- **核心逻辑**：在数据库层面为 `fore_adjust_factor` 和 `back_adjust_factor` 增加明文注释，标记其废弃状态或兼容用途。
- **文档同步**：更新项目根目录下的 `TABLES_INDEX.md`，同步废弃说明和替代方案。
- **治理规范**：遵循 `AGENTS.md` 2.4 节，Schema 变更记录于 `migrations/` 目录。

## 依赖认证
- **数据表**：`stock_adjust_factor` (MySQL 5.7)。
- **文档**：`docs/TABLES_INDEX.md`。
- **权限**：需具备对 `stock` 库执行 `ALTER TABLE` 的权限。

## 架构溯源与风险认证
- **激活角色**: [DB Auditor], [Data Quality Steward], [Workflow Guard]
- **风险**:
    - **锁表风险**：虽然 `MODIFY COLUMN` 仅更新元数据（元数据锁），但在高并发生产环境下仍需注意。
    - **兼容性**：仅添加注释不影响数据读写，但需确保 DDL 语法在 MySQL 5.7 中完全兼容。
- **缓解措施**：
    - 在盘后或业务低峰期执行。
    - DDL 严格按照 `SHOW CREATE TABLE` 返回的原始列定义（类型、精度）进行编写，仅修改 COMMENT。

## 方案设计

### 1. DDL 执行 (T1)
在 `scf-collector/migrations/` 下创建 `20260513_E8_S2_deprecate_adj_fields.sql`。
执行 `ALTER TABLE` 语句：
- `fore_adjust_factor`: 增加“已废弃”注释。
- `back_adjust_factor`: 增加“legacy 兼容”注释。

### 2. 文档同步 (T2)
修改根目录 `docs/TABLES_INDEX.md`。
在 `ods_adjust_factor` (或相关条目) 增加备注。

## 任务列表 (Tasks)
- [ ] **E8-S2-T1**: 编写并执行 DDL 迁移脚本，更新数据库注释。
- [ ] **E8-S2-T2**: 更新 `docs/TABLES_INDEX.md` 中的字段说明。
- [ ] **E8-S2-T3**: 验证数据库注释是否生效。

## 验收标准 (AC)
- **AC1: 数据库注释生效**
    - Given: 执行 DDL 成功。
    - When: 执行 `SHOW FULL COLUMNS FROM stock_adjust_factor`。
    - Then: 对应字段的 `Comment` 列显示预期的废弃说明。
- **AC2: 文档一致性**
    - Given: `TABLES_INDEX.md` 已更新。
    - When: 查阅该文档。
    - Then: 明确看到 `fore_adjust_factor` 的废弃标记。
