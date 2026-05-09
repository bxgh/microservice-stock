# Epic E100: Agent 治理体系从“口头约定”到“模块化门禁”的重构

**目标**: 将 41 服务器验证通过的 v1.2 治理体系迁移并适配至本仓库，通过角色化治理和自动化审计，确保开发质量 100% 符合工程标准。
**前置依赖**: 无

---

## E100-S1: AGENTS.md 升级与规约解耦

**用户故事**: 作为开发负责人，我希望将 AGENTS.md 重构为模块化结构，以便降低 Agent 的认知负荷，并使技术标准更易于维护。

#### 任务
- [ ] **E100-S1-T1**: 迁移 `.agent/rules/python-coding-standards.md` 并适配腾讯云环境
- [ ] **E100-S1-T2**: 重构 `AGENTS.md` 至 v1.2，剥离技术细节并建立模块化引用
- [ ] **E100-S1-T3**: 建立根目录准入白名单约束

#### 验收标准(AC)
1. **Given** 存在 `.agent/rules/python-coding-standards.md` **When** 查阅 `AGENTS.md` **Then** 应能看到明确的模块化跳转说明。
2. **Given** 开发过程中新建文件 **When** 文件不在白名单且在根目录 **Then** Agent 应能主动识别并重定向至 `scratch/` 或 `scripts/`。

---

## E100-S2: 引入 ROLES.md 建立角色化责任闭环

**用户故事**: 作为 Agent，我希望有明确的角色定义，以便在不同开发阶段（如 DDL、API 开发、QA）自动激活特定的审计逻辑。

#### 任务
- [ ] **E100-S2-T1**: 迁移 `docs/architecture/agent-skill-rules/ROLES.md` 并注册角色
- [ ] **E100-S2-T2**: 在实施流程中强制显式声明激活角色

#### 验收标准(AC)
1. **Given** 涉及数据库修改 **When** 编写实施计划 **Then** 必须显式声明激活 `[DB Auditor]` 角色。
2. **Given** 编写 `walkthrough.md` **When** 交付成果 **Then** 必须包含各激活角色的审计陈述。

---

## E100-S3: 物理门禁：自动化审计脚本迁移

**用户故事**: 作为系统管理员，我希望通过脚本强制执行 DDL 和数据单位规范，以杜绝人为疏忽造成的生产事故。

#### 任务
- [ ] **E100-S3-T1**: 迁移 `.agents/scripts/data_validator.py` 并适配本仓单位规范
- [ ] **E100-S3-T2**: 迁移 `.agents/scripts/schema_enforcer.py` 用于强制 DDL 审计
- [ ] **E100-S3-T3**: 迁移 `workflow_auditor.py` 等辅助审计工具

#### 验收标准(AC)
1. **Given** 一段不包含 `is_deleted` 的 DDL **When** 运行 `schema_enforcer.py` **Then** 应返回明确的违规错误。
2. **Given** 包含 `pct_chg > 1` 的数据文件 **When** 运行 `data_validator.py` **Then** 应发出单位异常告警。

---

## E100-S4: 标准化交付模板实施

**用户故事**: 作为审计员，我希望所有实施日志具有一致的结构和“真源证据”，以便快速核查开发真实性。

#### 任务
- [ ] **E100-S4-T1**: 建立 `.agents/templates/` 目录并迁移标准模板
- [ ] **E100-S4-T2**: 更新 `implementation_plan.md` 模板，加入 Readiness Check 与架构溯源

#### 验收标准(AC)
1. **Given** 开始新 Story **When** 初始化 implementation_logs **Then** 必须使用包含角色声明和架构溯源的最新模板。
