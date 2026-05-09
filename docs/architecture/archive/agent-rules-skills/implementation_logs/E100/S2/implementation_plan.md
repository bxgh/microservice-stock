# Implementation Plan - E100-S2: 引入 ROLES.md 建立角色化责任闭环

本项目旨在引入虚拟角色体系，通过 `ROLES.md` 明确定义 `[DB Auditor]`, `[Workflow Guard]` 和 `[Infra Specialist]` 的职责边界，解决 Agent 在长对话中由于上下文丢失而导致的规约遗忘问题。

## User Review Required

> [!IMPORTANT]
> - 本次变更将正式启用角色化思维链。Agent 在以后的每一个 `implementation_plan.md` 中都必须显式声明其激活的角色。
> - `ROLES.md` 将存放在 `docs/architecture/` 目录下。

## 架构溯源与风险认证
- **架构模式**: 虚拟角色治理 (Role-based Governance)。
- **保障机制**: 通过思维链强制对齐角色禁令。
- **激活角色**: `[Workflow Guard]`, `[Governance Lead]`

## 需求解析 (Readiness Check)
- **业务位置**: 系统级治理标准建设。
- **核心逻辑**: 迁移 -> 注册 -> 强制激活。
- **依赖认证**: 已获取 41 服务器 `ROLES.md` 源码。
- **TBD 销账**: 无。

## Proposed Changes

### 角色体系建设

#### [NEW] [ROLES.md](file:///home/ubuntu/microservice-stock/docs/architecture/ROLES.md)
- 迁移并注册三大核心角色：
    - `[DB Auditor]`: 负责 SQL、DDL、单位审计。
    - `[Workflow Guard]`: 负责流程准入、AC 覆盖、真源证据。
    - `[Infra Specialist]`: 负责部署、网络、数据流控制。

### 流程集成

#### [MODIFY] [AGENTS.md](file:///home/ubuntu/microservice-stock/AGENTS.md) (Section 5.1)
- 强制要求在 Readiness Check 中加入“角色激活”项。

## Verification Plan

### Automated Tests
- 无。

### Manual Verification
- 验证 Agent 是否能准确说出各角色的核心禁令（No-Go List）。
- 验证后续 Story 是否能正确激活角色。
