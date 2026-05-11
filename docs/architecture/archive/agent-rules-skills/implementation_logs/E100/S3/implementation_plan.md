# Implementation Plan - E100-S3: 物理门禁：自动化审计脚本迁移

本项目旨在通过自动化脚本强制执行 `AGENTS.md` 中的命名、单位和 DDL 规范。将 41 服务器的治理脚本迁移至本仓库，并进行环境适配。

## User Review Required

> [!IMPORTANT]
> - 本次变更将引入 `.agents/scripts/` 目录。
> - 在后续的 DDL 变更和数据入库任务中，必须强制先运行这些审计脚本。

## 架构溯源与风险认证
- **架构模式**: 自动化审计门禁 (Automated Governance Gates)。
- **保障机制**: 通过脚本静态分析 DDL 和样本数据。
- **激活角色**: `[DB Auditor]`, `[Workflow Guard]`

## 需求解析 (Readiness Check)
- **业务位置**: 核心治理工具链建设。
- **核心逻辑**: 脚本迁移 -> 逻辑适配 (如单位检查) -> 工具化集成。
- **依赖认证**: 已获取 41 服务器脚本源码。
- **TBD 销账**: 无。

## Proposed Changes

### 审计工具链建设

#### [NEW] [.agents/scripts/data_validator.py](file:///home/ubuntu/microservice-stock/.agents/scripts/data_validator.py)
- 迁移并适配：
    - `pct_chg`: 必须为小数 (0.0123)。
    - `amount`: 必须为元。
    - `ts_code`: 必须符合 `000001.SZ` 格式。

#### [NEW] [.agents/scripts/schema_enforcer.py](file:///home/ubuntu/microservice-stock/.agents/scripts/schema_enforcer.py)
- 迁移并适配：
    - 强制检查 `created_at`, `updated_at`, `is_deleted`。
    - 强制检查 `idx_updated_at`。

#### [NEW] [.agents/scripts/extract_truth.py](file:///home/ubuntu/microservice-stock/.agents/scripts/extract_truth.py)
- 辅助脚本，用于从数据库提取样本数据进行审计。

## Verification Plan

### Automated Tests
- 运行 `schema_enforcer.py` 审计本项目现有的 `migrations/`。
- 运行 `data_validator.py` 审计现有的 `ods_*` 样本数据。

### Manual Verification
- 验证脚本是否能正确拦截不规范的 DDL 和数据。
