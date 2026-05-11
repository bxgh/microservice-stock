# Implementation Plan - E{Epic}-S{Story}: {Title}

{Brief description of the change and background context.}

## 1. 需求解析
- {Point 1}
- {Point 2}

## 2. 依赖认证
- [ ] 所有引用的 `ods_*` / `ads_*` 表在 `TABLES_INDEX.md` 中已查实。
- [ ] 生产环境相关容器状态正常。
- [ ] 涉及 DDL 时，已通过 `skill:schema-enforcer` 验证规范。

## 3. 任务分解 (Task Breakdown)
- [ ] [E{Epic}-S{Story}-T1] {Task description}
- [ ] [E{Epic}-S{Story}-T2] {Task description}

## 4. 架构溯源与风险认证
- **激活角色**: {e.g., [DB Auditor], [Workflow Guard]}
- **保障机制**: {e.g., 通过 Gate-3 审计一致性，通过 skill:data-validator 拦截单位陷阱}

## 5. 验证计划
- **Automated Tests**: {Exact commands to run}
- **Manual Verification**: {True Source extraction command}
