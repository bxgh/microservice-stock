---
name: epic-story-doc
description: 用 Epic → Story → Task → AC 层级结构生成结构化工程文档。在用户请求编写或重写以下任意类型文档时主动使用：PRD / 产品需求文档、技术设计文档（TDD）、架构说明 / 架构设计、系统改造方案 / 重构方案、迁移方案、实施方案 / 实现方案、项目 README、工程交付文档、详细设计、技术评审材料。也在用户提到「拆 Epic」「拆 Story」「写用户故事」「拆任务」「Given-When-Then」「验收标准」时使用。即使用户只说「写个方案」「整理一份文档」「帮我做个设计」，但上下文是工程/技术场景，也应使用本 skill。本 skill 不适用于：纯文案、博客、营销文、个人简历、与软件工程无关的报告。
---

# Epic-Story 工程文档生成

按 Epic → Story → Task → AC 四层结构产出技术文档。每次生成必须同时输出两个文件：`draft_{EpicId}.md`（git 存档）和 `draft_{EpicId}.json`（供评审台加载）。

---

## 核心原则

- **AC 可测试性**: 每条 AC 必须是 Given-When-Then 格式，Then 必须包含可观测的具体事实（数值、状态、文件名等）
- **项目归口原则**: 设计文档（MD/JSON）必须存放于对应微服务的 `docs/features/{feature_name}/design/` 目录下。全局设计存放于 `docs/domains/{domain_name}/`。
- **门户集成**: 设计完成后必须运行 `scripts/update_docs_portal.py` 同步到项目门户。
- **角色具体性**: `role.as` 必须是具体角色（如 `scf-collector`、`DB Auditor`），不写「用户」
- **Task 可执行性**: 每条 Task 对应一个原子操作，可被单独分配和验收
- **字段一致性**: 字段名、单位、口径必须与 `PROJECT_OVERVIEW.md` 和 `TABLES_INDEX.md` 一致
- **防御性设计**: 每个外部依赖必须在 AC 中声明降级策略

---

## 双格式输出规范

每次生成或重生成文档时，必须同时输出：

| 文件 | 格式 | 用途 |
|---|---|---|
| `draft_{EpicId}.md` | Markdown | 人类可读，存入 git 版本管理 |
| `draft_{EpicId}.json` | JSON | 结构化数据，供评审台加载 |

生成后，用户运行 `python inject.py draft_{EpicId}.json` 即可生成自包含评审 HTML。

---

## 评审台 JSON Schema

### 完整结构

```json
{
  "title": "文档标题",
  "version": "v0.1",
  "date": "YYYY-MM-DD",
  "sections": [
    {
      "id": "background",
      "title": "背景",
      "blocks": [
        { "type": "text", "content": "背景说明" },
        { "type": "formula", "content": "P_{adj} = P_{raw} \\times \\frac{F_{latest}}{F(t)}" },
        { "type": "mermaid", "content": "flowchart LR\n  A --> B" },
        { "type": "table", "content": [["列1","列2"],["值1","值2"]] },
        { "type": "code", "lang": "sql", "content": "SELECT * FROM t;" }
      ]
    }
  ],
  "risks": [
    { "risk": "描述", "impact": "高|中|低", "prob": "高|中|低", "mitigation": "措施" }
  ],
  "milestones": [
    { "name": "M1", "date": "YYYY-MM-DD", "deliverable": "交付物" }
  ],
  "epics": [
    {
      "id": "E1",
      "title": "Epic 标题",
      "desc": "Epic 描述：交付什么独立价值，预计耗时",
      "stories": [
        {
          "id": "E1-S1",
          "title": "Story 标题",
          "role": {
            "as": "具体角色（如：scf-collector）",
            "want": "可观察的功能行为",
            "value": "具体业务价值"
          },
          "tasks": [
            { "id": "E1-S1-T1", "text": "可执行任务描述" }
          ],
          "acs": [
            {
              "id": "AC1",
              "name": "AC 名称",
              "given": "前置条件",
              "when": "触发动作",
              "then": "可验证的预期结果（含具体数值/状态）"
            }
          ]
        }
      ]
    }
  ]
}
```

### Block 类型说明

| type | 用途 | content 格式 |
|---|---|---|
| `text` | 普通文本，支持 `$...$` 行内公式 | 字符串 |
| `formula` | 独立公式块（块级显示） | LaTeX 字符串，不含 `$$` |
| `mermaid` | 流程图/架构图/时序图 | Mermaid 语法字符串 |
| `table` | 结构化表格 | 二维数组，第一行为表头 |
| `code` | 代码块，需附 `lang` 字段 | 代码字符串 |

### 输出规范

- **只输出 JSON，不含任何其他内容**（不含 markdown 代码块、不含说明文字）
- 不确定的字段填写 `"TBD"`，不编造数据
- `risks` 和 `milestones` 若无信息输出空数组 `[]`
- 每个 Story 至少 2 条 AC，少于 2 条说明 Story 粒度过粗
- JSON 必须可被 `JSON.parse()` 直接解析，不允许注释或 trailing comma
- 字符串内如需使用双引号，改用中文引号「」或『』

---

## 重生成规则

收到评审台导出的 `review_result.json` 时：

| 字段 | 处理方式 |
|---|---|
| `story_reviews[].status = "no"` | 根据 `comment` 字段修改整个 Story 后重新生成 |
| `story_reviews[].ac_list[].status = "no"/"q"` | 根据 `question` 字段修改对应 AC 的 Given-When-Then |
| `story_reviews[].ac_list[].status = "ok"` 或无意见 | 保持原内容不变 |
| `task_changes[].removed = true` | 从文档中删除该 Task，编号不补位 |
| `task_changes[].modified_text != null` | 使用修改后的文本替换原任务描述 |
| `task_changes[].added != null` | 作为新 Task 插入对应 Story 末尾 |
| `section_comments[]` | 在对应章节末尾以 `> **评审批注**:` 格式追加 |
| `agent_instruction` | 按指示递增版本号，追加变更记录 |

---

## 激活角色声明示例

在 `implementation_plan.md` 中声明：
> **激活角色**: [Requirement Architect], [Backend Engineer], [DB Auditor]

---

## 完整示例

读取 `references/full-example.md` 查看完整文档示例。
