# Implementation Plan - E100-S3 数据质量 QC 准则优化与标准化

> **激活角色**: [Requirement Architect], [Workflow Guard], [Data Quality Steward]
> **溯源**: 关联 `AGENTS.md` 5.3 节 (真源准则) 及 E1-S1 实施中的现金流量表 Bug 复盘。

## 1. 任务背景
在 E1-S1 (财务数据接入) 实施过程中，由于缺乏多表联动的全字段比对及强制性的空值校验，导致现金流量表映射错误且未能及时发现。现需将“数据质量抽验”从可选任务提升为“系统硬约束”，通过角色增强和流程标准化杜绝此类低级错误。

## 2. 方案目标
- [x] **角色增强**: 在 `ROLES.md` 的 `[Data Quality Steward]` 中增加“首条记录全对齐”与“核心字段非空校验”红线。
- [x] **流程对齐**: 在 `AGENTS.md` 中新增 `5.4 数据质量闭环 (QC Feedback Loop)`。
- [x] **工具标准化**: 建立标准的 QC 脚本模板，要求所有数据接入 Story 必须产出对应的 `qc_*.py` 脚本。
- [x] **证据标准化**: 在 `walkthrough.md` 模板中强制引入“字段映射对齐表”。

## 3. 核心约束 (No-Go List 预览)

### [Data Quality Steward] 增强禁令：
- ❌ **映射盲目**: 严禁在未输出“首条记录 API vs DB 对比矩阵”的情况下宣称映射完成。
- ❌ **批量回填风险**: 严禁在未通过“10 条记录灰度 QC”的情况下启动全量（>1000 条）历史同步。
- ❌ **核心字段容忍**: 严禁在核心事实字段（如 `total_assets`, `net_profit`, `eps`）存在超过 1% 的 NULL 率或 0 值率时跳过报错。

## 4. 验收标准 (AC)

#### AC-1: 准则文件更新
- **Given** 修改 `ROLES.md` 和 `AGENTS.md`
- **When** 涉及数据接入任务
- **Then** 必须在 `implementation_plan.md` 中显式包含“QC 灰度验证”阶段。

#### AC-2: 证据链闭环
- **Given** 编写 `walkthrough.md`
- **When** 涉及 `ods_` 层表入库
- **Then** 必须包含 `COUNT(*) WHERE field IS NULL` 的查询结果作为证据。

## 5. 任务拆解
- [ ] **E100-S3-T1**: 更新 `ROLES.md`，增强 `[Data Quality Steward]` 角色的禁令。
- [ ] **E100-S3-T2**: 更新 `AGENTS.md`，新增“数据质量闭环”章节及灰度同步要求。
- [ ] **E100-S3-T3**: 在 `docs/architecture/` 下创建 `QC_GUIDELINES.md` 作为通用检查清单。
- [ ] **E100-S3-T4**: 应用新准则，重新验证 E1-S1 的修复结果。
