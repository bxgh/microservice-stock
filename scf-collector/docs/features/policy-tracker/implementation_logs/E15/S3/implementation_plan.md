# E15-S3: 规则路径灰度审计与正式切流实施方案

> **版本**: v1.0  
> **起草日期**: 2026-05-18  
> **状态**: Draft for Review  
> **依赖**: E15-S1 与 E15-S2 (M1/M2 里程碑) 已上线，并于 CDB 正常运行

---

## 需求解析与设计真源

### 1. 核心逻辑 (3句话描述)
- **影子双写对照**: 启用 `RULE_BASED_PATH_ENABLED = "shadow"`，新匹配政策由规则处理器处理并写入影子表 `dwd_policy_analysis_shadow`，同时主线仍走 LLM 写入 `dwd_policy_analysis` 以保护生产环境.
- **自动审计比对**: 编写自动化比对脚本 `scf-collector/scripts/audit_policy_rules.py`，拉取重叠政策，对重要性、强度、板块、及核心摘要语义进行 5 维一致率比对.
- **正式切流切回**: 比对一致率连续 7 天 ≥ 95% 后，安全升级环境变量为 `"production"` 停用影子写入实现正式切流；准备 rollback 脚本保底在异常时 1s 内切回大模型.

### 2. 架构溯源与风险认证
- **关联设计文档**: [E15_AI_Efficiency_Cost_Optimization_v1.0.md](file:///e:/gitee/microservice-stock/scf-collector/docs/features/policy-tracker/design/E15_AI_Efficiency_Cost_Optimization_v1.0.md#L173-L196)
- **激活角色**: `[Requirement Architect]`, `[Backend Engineer]`, `[Workflow Guard]`, `[QA/Test Engineer]`
- **依赖说明**: 需确认 MySQL 5.7 物理库中 `dwd_policy_analysis` 与 `dwd_policy_analysis_shadow` 表结构保持 100% 对齐，且 `staged_analyzer.py` 的 `"shadow"` 双写路由功能已安全稳定部署.

---

## User Review Required (用户评审要点)

> [!IMPORTANT]
> **设计概念修正 (影子模式的写入目标对调)**
> - **原始设计描述**: "E1-S3-T1 启用双路并行模式:规则路径写主表,LLM 路径写影子表"
> - **安全与防污染纠正**: 在实质代码落地中，为了极致保障生产环境不受任何未经完整校验的规则解析器的格式或板块污染，我们采取了**更安全的"反向影子"设计**（即：LLM 路径继续写入生产主表 `dwd_policy_analysis`，规则路径静默写入影子对照表 `dwd_policy_analysis_shadow`）.
> - **切流逻辑**: 在本期比对通过后，一旦切流到 `"production"` 模式，规则路径将转为直切写入主表，同时完全跳过 LLM 路径，实现 100% 的 Token 节省.
> - **请用户确认**: 此安全防污染设计已于 `StagedAnalyzer` 核心层代码中生效，本实施计划将完全基于该物理对账策略进行灰度审计和比对，请予以批准.

---

## Open Questions (待确认事项)

> [!NOTE]
> **1. 板块 Jaccard 一致性判定阈值**
> 规则提取器输出的 positive/negative 板块往往非常精确（如 OMO 对地产、银行等）。LLM 解读的板块可能相对宽泛。我们对板块比对采用 **Jaccard 相似度** (交集/并集)。建议将板块的警告阈值设为 Jaccard Similarity ≥ 0.6，人工抽检语义大于 90%，这能有效平抑 LLM 输出的宽泛噪声.
>
> **2. 语义一致性计算方案**
> summary 字段是长文本。比对脚本将结合:
> - **Simhash / 汉明距离**: 比对两路 summary 的哈希距离.
> - **长度对比与关键指标抓取**: 利用正则表达式提取 summary 中的降息 bp 数、LPR 数字、逆回购天数 and 金额等核心量纲，要求量纲 100% 精确对齐.

---

## Proposed Changes (拟作出的修改)

### 1. 新增比对审计脚本

#### [NEW] [audit_policy_rules.py](file:///e:/gitee/microservice-stock/scf-collector/scripts/audit_policy_rules.py)
编写高性能、异步的 5 维一致率比对脚本。主要步骤为：
- 查询 `dwd_policy_analysis` (LLM 生产表) 与 `dwd_policy_analysis_shadow` (规则影子表) 中 `policy_id` 重合且由同一规则提取器匹配的对照组记录。
- 执行 5 维对账比对：
  1. **重要性星级比对**: `importance_level` 必须 100% 一致.
  2. **政策强度对比倾向**: `intensity_change` 方向（`stronger`, `weaker`, `neutral`）必须匹配.
  3. **量纲匹配提取 (LPR/OMO/MLF)**: 利用正则抽取 summary 中的数字（如 `3.10%`, `20亿元`, `7天` 等），误差必须为 0.
  4. **板块相似度比对 (Jaccard)**: 对 positive/negative 板块列表转换为 SW 板块编码集合进行交并比计算，相似度 ≥ 0.60 记为合格.
  5. **Simhash 语义比对**: 对两路 summary 内容进行 Simhash 距离核算.
- 统计近 7 天的所有对照数据，计算整体一致率，当数据条数 ≥ 30 且综合一致率 ≥ 95% 时，打印 "AUDIT STATUS: PASS"，否则打印 "AUDIT STATUS: WARNING / FAIL".
- 自动将报告输出为 Markdown / HTML 文件，并触发 Portal 更新.

### 2. 测试集加固

#### [NEW] [test_audit_policy_rules.py](file:///e:/gitee/microservice-stock/scf-collector/tests/test_audit_policy_rules.py)
- Given-When-Then 对比审计逻辑测试.
- 模拟 LPR 和 OMO 成功的匹配数据、以及故意捏造的不一致脏数据，验证 `audit_policy_rules.py` 能够精准抓取并报告所有偏差和不一致量纲.

### 3. 切流与回退运维指南

#### [NEW] [playbook_cutover_rollback.md](file:///e:/gitee/microservice-stock/scf-collector/docs/features/policy-tracker/implementation_logs/E15/S3/playbook_cutover_rollback.md)
- 详细说明通过配置云托管环境或本地环境 `RULE_BASED_PATH_ENABLED="production"` 实现切流的步骤.
- 记录一键 rollback 脚本，通过设定 `RULE_BASED_PATH_ENABLED="shadow"` 或 `"disabled"` 强制切回原 LLM 路径的方案，确保 100% 高可用.

---

## AI 实施蓝图与提示词 (AI Implementation Blueprints)

> [!TIP]
> **Subagent 执行指南 (Plan-as-Prompt)**
> 
> 请 Subagent 在接收到执行任务时，严格按照以下步骤完成开发：
> 1. **物理环境验证**: 检查 CDB 连接池，使用 `test_staged_analyzer.py` 的测试机制，确保本地 and 云端数据库可以正常访问.
> 2. **独立模块开发**: 编写 `scripts/audit_policy_rules.py`，保持代码的异步处理、熔断防御和极简结构。所有 MySQL 5.7 的语句必须保持兼容性，`is_deleted = 0` 的查询必须被显式加上.
> 3. **百分百量纲比对**: 正则表达式必须足够强壮，能够捕获中文字符中的所有浮点数及百分号.
> 4. **HTML 全自动构建**: 所有修改 or 新增的 markdown 文档均须执行 `python scripts/md_to_html_premium.py <file>` 编译 HTML 副本并运行 `python scripts/update_docs_portal.py` 刷新 Portal 门户.

---

## Verification Plan (验证计划)

### 1. 自动化单元测试与回归测试
```bash
# 1. 运行分级路由单元测试，确保影子路由依旧稳固
python -m pytest tests/test_staged_analysis.py -v

# 2. 运行新增的比对逻辑单元测试
python -m pytest tests/test_audit_policy_rules.py -v
```

### 2. 影子模式物理测试沙盒 (Staging Run)
- 模拟运行 `python scripts/audit_policy_rules.py`，传入沙盒中的测试数据。
- 确认能成功导出 Markdown 及 HTML 格式的比对对账报告，并成功刷新文档门户.
