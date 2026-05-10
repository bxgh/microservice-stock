# E100-S1: 腾讯云环境治理同步与角色增强

> **激活角色**: [Requirement Architect], [Workflow Guard], [Infra Specialist]

## 1. 任务背景
当前仓库 (`microservice-stock`) 角色为**腾讯云端服务仓**，但存量治理文档 (`AGENTS.md`, `ROLES.md`) 中仍残留大量内网服务器 (Node-41) 及 Gost 隧道的约束，导致 Agent 在执行任务时产生认知偏置。

## 2. 方案目标
- [x] **环境对齐**: 移除 Node-41/Gost 依赖，明确云端生产环境约束。
- [x] **角色增强**: 引入 `[Requirement Architect]`、`[Data Quality Steward]` 等 4 个新角色，提升设计与数据质量。
- [x] **强制解耦**: 在开发阶段禁止新建硬编码 Cron，强制推行 Stage A-D 事件驱动架构。

## 3. 变更范围
- `AGENTS.md`: 更新 v1.3，同步反模式清单。
- `ROLES.md`: 扩展至 7 个角色，增加禁止 Cron 禁令。
- `docs/PROJECT_OVERVIEW.md`: 更新第 11 节部署环境描述。

## 4. 验收标准 (AC)
- **Given** 本仓为腾讯云环境 **When** 查看 `ROLES.md` **Then** 默认部署节点不应包含 Node-41。
- **Given** 新任务设计 **When** 涉及调度 **Then** Agent 必须主动识别并拦截 Cron 方案。
