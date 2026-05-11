# Walkthrough - E{Epic}-S{Story}: {Title}

## 实施概述
{Summary of what was accomplished.}

## 变更详情
{Key changes made in this story.}

## 验证结果 (Automated Evidence)
> [!IMPORTANT]
> 以下证据由自动化审计工具提取，包含物理指纹，严禁人为润色。

{INSERT_AUTOMATED_REPORT_HERE}

## 2. 验证结果 (True Source Evidence)

### AC 验证对比
| 验收标准 (AC) | 验证方法 | 物理证据 (代码块/截图) | 结果 |
|---|---|---|---|
| {Given-When-Then 1} | {e.g., SQL Select} | {Evidence} | PASS |
| {Given-When-Then 2} | {e.g., Docker Logs} | {Evidence} | PASS |

## 3. QA 自查清单 (Self-Audit)
- [ ] **[DB Auditor]**: 已确认所有 SQL 均包含 `is_deleted = 0` 且单位正确。
- [ ] **[Workflow Guard]**: 已确认静态扫描 `.agents/scripts/data_validator.py` 结果为 0 违规。
- [ ] **[Workflow Guard]**: 已确认 Git 提交 ID 与 Task ID 一一对应。
- [ ] **[Infra Specialist]**: 已确认结果集控制在 10,000 行以内。
