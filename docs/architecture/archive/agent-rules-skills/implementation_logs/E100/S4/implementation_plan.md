# Implementation Plan - E100-S4: 标准化交付模板实施

本项目旨在固化治理流程，通过标准化模板确保每一个 Story 的开发都有据可查，且符合 v1.2 的准入与验收准则。

## User Review Required

> [!IMPORTANT]
> - 本次变更将引入 `.agents/templates/` 目录。
> - 在后续的开发任务中，必须强制使用这些模板初始化实施日志。

## 架构溯源与风险认证
- **架构模式**: 标准化流程存证 (Standardized Process Documentation)。
- **保障机制**: 模板驱动的思维链约束。
- **激活角色**: `[Workflow Guard]`, `[Governance Lead]`

## 需求解析 (Readiness Check)
- **业务位置**: 治理体系闭环。
- **核心逻辑**: 模板定义 -> 目录固化 -> 强制执行。
- **依赖认证**: 已参考 41 服务器模板结构。
- **TBD 销账**: 无。

## Proposed Changes

### 模板库建设

#### [NEW] [.agents/templates/implementation_plan.template.md](file:///home/ubuntu/microservice-stock/.agents/templates/implementation_plan.template.md)
- 包含：角色激活、Readiness Check、架构溯源、Proposed Changes、Verification Plan。

#### [NEW] [.agents/templates/walkthrough.template.md](file:///home/ubuntu/microservice-stock/.agents/templates/walkthrough.template.md)
- 包含：Story 摘要、真源证据 (SQL/Logs)、角色审计报告。

#### [NEW] [.agents/templates/final_report.template.md](file:///home/ubuntu/microservice-stock/.agents/templates/final_report.template.md)
- 包含：Epic 达成情况、资产清单、核准信息。

## Verification Plan

### Automated Tests
- 无。

### Manual Verification
- 检查模板内容是否涵盖了 `AGENTS.md` v1.2 和 `ROLES.md` 的所有强制项。
