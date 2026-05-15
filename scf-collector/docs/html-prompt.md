请将我提供的 Epic-Story 文档（或需求描述）转换为以下 JSON 格式，用于 HTML 评审台加载。
只输出 JSON，不要输出任何其他内容（不要 markdown 代码块，不要说明文字）。

{
  "title": "文档标题",
  "version": "v0.1",
  "date": "YYYY-MM-DD",
  "background": "背景描述",
  "objective": "目标（可量化）",
  "scope": "范围",
  "out_of_scope": "非目标",
  "risks": [{"risk":"描述","impact":"高|中|低","prob":"高|中|低","mitigation":"措施"}],
  "milestones": [{"name":"名称","date":"YYYY-MM-DD","deliverable":"交付物"}],
  "epics": [{
    "id": "E1", "title": "Epic标题", "desc": "描述",
    "stories": [{
      "id": "E1-S1", "title": "Story标题",
      "role": {"as":"具体角色","want":"可观察功能","value":"具体价值"},
      "tasks": [{"id":"E1-S1-T1","text":"任务描述","code":"代码块或脚本(如有)"}],
      "acs": [{"id":"AC1","name":"AC名称","given":"前置条件","when":"触发动作","then":"预期结果"}]
    }]
  }]
}

规则：
1. 每个 Story 至少 2 条 AC，AC 必须是可测试的 Given-When-Then。
2. 必须提取文档中的 SQL、Bash、Python 等核心代码块，并放入对应 Task 的 "code" 字段中。如果一个代码块对应多个任务，请放在最相关的那个任务中。
3. 不确定填 "TBD"。
