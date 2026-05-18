# Implementation Plan - E15-M7: E6 增量(Diff)分析落地与集成

本方案针对 AI 政策分析引擎的 Milestone M7（里程碑 7）进行详细设计与实施规划。该里程碑聚焦于 **E6 增量(Diff)分析** 降本Story的闭怀开发：
1. **E6-S1 政策相似度检测**：利用已实现的 SimHash (64位) 汉明距离计算，从数据库快速定位同一发布方（`ts_code`）和同分类（`policy_type`）的历史相似基准（已完成哈希及查询部分）。
2. **E6-S2 Diff 提取与 Prompt 设计**：对汉明距离 ≤ 3 的高度相似政策（如月度 LPR、MLF/逆回购例行公告、例行行政公示等），提取其核心段落（`segment_used`）的文本差异（Diff），将 **“上期分析摘要” + “本期文本变化(Diff)”** 作为极简输入送入 LLM 进行边际变化（Marginal Change）对比。本方案能大幅度削减大模型的输入 Token 消耗（长文档降幅可达 60% - 90%），完美贴合 DeepSeek 缓存机制，实现极限成本压缩。

---

## 需求解析与核心逻辑 (3句话)

1. **精准文本差分提取**：设计轻量且对中英文均高兼容的 `diff_helper`，以句子/段落级差分对本期核心段落（`segment_used`）与上期核心段落执行快速 `unified_diff`，剥离出仅包含新增（`+`）或修改（`-`）的关键差异行。
2. **边际分析 Prompt 契约**：设计全新静态化、缓存友好型的 `WORDING_DIFF_SYSTEM_V1` 提示词，使大模型仅根据“上期摘要”与“差分文本”进行逻辑推导，生成对齐 `WordingContrastOutput` 的标准边际变化 JSON。
3. **二阶段相似分流拦截**：在 `StagedAnalyzer` 二阶段分流中检测 `similarity_rating == 'high'` (距离 ≤ 3) 的 4 星（或 3 星升级）政策，拦截标准 LLM 分析路径并将其重定向至 `'llm_diff'`（Diff 模式），将 `analysis_path` 保存为 `'llm_diff'`，同时与上期 `contrast_baseline_id` 物理关联。

---

## 激活角色说明

*   `[Requirement Architect] (需求与方案架构师)`：激活并保障 Diff 差分的高召回、零漏报、以及 Given-When-Then 的 AC 测试闭环。
*   `[Backend Engineer] (后端工程专家)`：负责 `diff_helper.py` 的算法细节、`prompts.py` 中 `WORDING_DIFF_SYSTEM_V1` 静态 Prompt 垫厚、以及 `staged_analyzer.py` / `policy_analyzer.py` 的路由桥接与异步安全。
*   `[QA/Test Engineer] (自动化测试专家)`：负责构建 `test_m7_features.py`，完整物理模拟高度相似政策从初筛、差分、LLM 调用、到 `'llm_diff'` 零漏报落库的端到端 QC 回归。
*   `[Workflow Guard] (流程质量哨兵)`：实施双跑与质量审计，确保物理证据链（SQL/日志）存证，并完成 Portal 双向编译更新。

---

## User Review Required

> [!IMPORTANT]
> **1. 5 星超重磅政策的 Diff 豁免策略**
> *   出于投资决策的极端严谨性，**5 星（或置信度低于 0.7 强制升级的 5 星级）政策将不触发 Diff 分析**。这类重大宏观转折政策（如中央经济工作会议、央行重大降准降息声明）即便与历史文本看似高度相似，其细微语义也必须获得最高算力解析。因此，5 星级重大政策将保持现有 `triage_and_voting`（3 次 pro-thinking 多数投票）流程，以保证质量零妥协。
> 
> **2. 申万行业板块的继承与对比合并**
> *   在 Diff 模式中，大模型主要读取“上期摘要”与“本期差异”。有些不受差异影响的利好板块（如上期政策判断 LPR 下调利好房地产/银行，本期 LPR 维持不变）可以通过大模型在 Diff 过程中自动从上期摘要继承，或根据本期 Diff（如未调整）进行持平微调。我们在 Prompt 中对 LLM 进行了显式指令强化，确保 `sectors` 与 `intensity_change` 能够合理推导并完美对齐。
> 
> **3. 环境变量降级开关 (Feature Flag)**
> *   我们提供 `DIFF_ANALYSIS_ENABLED` 环境变量（默认 `true`），若在生产环境发现因 Diff 算法产生语义丢失或下游解析偏差，可随时通过将其设为 `false`，全局热切换回 E14 标准双期全文对比模式，实现 100% 零风险隔离。

---

## Open Questions

> [!NOTE]
> **Q1: 使用 difflib 的 unified_diff 还是 ndiff 算法？**
> *   **决策**：使用 `difflib.unified_diff` 并设定 `n=1`（1行上下文）。
> *   **理由**：`ndiff` 包含大量的逐字符微调对比符号（如 `?`），对于大模型而言易产生格式混淆；而 `unified_diff` 的格式更为直观、干净（仅输出含有 `+` 和 `-` 的变化行与极少量上下文），其 Token 消耗极低，大模型在理解 unified diff 语义时已被证实具有极高的稳定度。

---

## Proposed Changes

### Component: Diff Computation & Prompt Core

---

#### [NEW] [diff_helper.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/diff_helper.py)
*   **修改内容**：新增纯 Python 文本差分辅助模块。
*   **核心逻辑**：
    1.  `clean_lines(text)`: 将输入文本按句号（`。`）、分号（`；`）或换行（`\n`）拆分成独立的语义句子，去除前后空白，过滤空行。
    2.  `generate_text_diff(prev_text, curr_text) -> str`: 利用 `difflib.unified_diff` 对拆分后的句子列表进行对比，过滤文件头（`---`, `+++`, `@@`），保留带 `+` 和 `-` 的差异内容并输出。
    3.  如果对比后发现差异完全为空，返回 `"【无文本差异】"`, 防止模型产生无谓的幻觉。

---

#### [MODIFY] [prompts.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/prompts.py)
*   **修改内容**：添加 `WORDING_DIFF_SYSTEM_V1` 静态 System Prompt 垫厚。
*   **系统提示词大纲**：
    1.  **角色定义**：顶级宏观战略分析师，处理微小边际增量变化。
    2.  **契约映射**：输出必须符合 `WordingContrastOutput` 的标准 JSON Schema (重用 schema 保持下游零感知)。
    3.  **Few-Shot Cases**：显式注入带有 Diff 输入 and JSON 输出的 Few-Shot 对照示例（例如 LPR 利率在上期 3.10% 下调至 3.05% 的 Diff 对比分析），训练模型精准捕捉 `intensity_change` 倾向并完美继承/修正受影响的申万板块。

---

### Component: Analysis Routing & Gateway Control

---

#### [MODIFY] [staged_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/staged_analyzer.py)
*   **修改内容**：在 Stage 2 分流器中，针对高相似度（Hanmming Distance <= 3）且重要性为 4 星的政策，截断标准深度分析，引入 Diff 分析通路。
*   **核心逻辑**：
    1.  在分流逻辑处（`importance == 4` 判定分支），新增 `DIFF_ANALYSIS_ENABLED` 检测。
    2.  若 `similar_info` 且其 `similarity_rating == "high"`:
        *   从 `dwd_policy_analysis` 中通过 `matched_analysis_id` 异步加载上期的 `summary` 与 `segment_used`。
        *   调用 `generate_text_diff` 生成两期核心文本差分 `diff_text`。
        *   重定向至 `PolicyAnalyzer.analyze_policy`，显式传递 `force_deep_mode='diff_only'`, `previous_summary=...`, `diff_text=...`, `contrast_baseline_id=...`, `analysis_path='llm_diff'`。
        *   路由成功后，注入 `'routing_path' = 'triage_and_diff'`。

---

#### [MODIFY] [policy_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/policy_analyzer.py)
*   **修改内容**：
    1.  更新 `analyze_policy` 函数签名，追加可选参数：`previous_summary`、`diff_text`、`contrast_baseline_id`。
    2.  当 `force_deep_mode == 'diff_only'` 时：
        *   `mode` 依据 `reasoning_effort` 判定是否为 `pro-thinking`（思考模型）或 `deep`
        *   `system_prompt` 切换至 `prompts.WORDING_DIFF_SYSTEM_V1`。
        *   `user_prompt` 组装为：`【上期分析摘要】\n{previous_summary}\n\n【本期文本变化(Diff)】\n{diff_text}`。
        *   `prompt_name = "WORDING_DIFF_V1"`, `prompt_version = "1.0"`, 确保缓存统计前缀完美固定。
        *   JSON schema 解析强制指向 `WordingContrastOutput`。
        *   落库时，保留 `contrast_baseline_id`，且在 DB 中保存 `'llm_diff'` 标志。

---

## AI 实施蓝图与提示词 (Plan-as-Prompt)

> [!IMPORTANT]
> **Subagent 执行指南 (必读)**
> 1.  **极简 unified_diff n=1 控制**：在 `diff_helper.py` 中，切分句子时要将常见的标点符号（如 `。`、`；`、`\n`）作为切分点，并使用 `strip()` 移除干扰项。生成 diff 时，使用参数 `n=1`（1行上下文），以实现对 Token 数量的极限控制。
> 2.  **5星政策硬性豁免**：在 `staged_analyzer.py` 的路由中，必须首先确认 `importance != 5`，即使相似度为 high 也决不能对 5 星政策开启 Diff 分析，必须坚决执行 `triage_and_voting`。
> 3.  **Schema 双重匹配**：在 `policy_analyzer.py` 中，当 `force_deep_mode == 'diff_only'` 时，`robust_parse_json` 必须以 `WordingContrastOutput` 作为 target_model，且最终落入 `dwd_policy_analysis` 时需要把 JSON 解析所得的 `contrast_details`（`key_diff_str`）、`intensity_change` 和 `implication` 对应落库。
> 4.  **Markdown HTML 自动刷新**：代码编写完成后，必须执行 `python scripts/md_to_html_premium.py scf-collector/docs/features/policy-tracker/implementation_logs/E15/M7/implementation_plan.md` 编译出对应的 HTML 并刷新文档门户！

---

## Verification Plan

### Automated Tests
*   **Milestone M7 特性集成测试**：
    *   我们将在 `scf-collector/tests/test_m7_features.py` 中编写标准 Given-When-Then 集成测试。
    *   **差分算法测试**：输入两段高相似 LPR 政策段落，验证 `diff_helper` 输出中仅提取出数字变动的行，并包含 `+` / `-` 符号，长度缩减 80% 以上。
    *   **StagedAnalyzer 路由分流测试**：Mock 一个高度相似（距离=1）的 4 星历史政策。当新政策到达时，验证系统判定 `routing_path == 'triage_and_diff'`，且未拉起常规 double-period 全文对比，而是重定向至 `diff_only` 链路。
    *   **LLM 费用与数据契约审计**：验证在 `diff_only` 模式下，落库的 `analysis_path == 'llm_diff'`，且 `contrast_baseline_id` 与上期正确锚定。
    *   **运行命令**：
        ```powershell
        $env:PYTHONPATH="."; pytest scf-collector/tests/test_m7_features.py -s -v
        ```

### Manual Verification
*   在 sandbox 开发库中插入两条高度相似的 ods 数据，利用 `StagedAnalyzer` 进行分析，验证其全链路能无缝完成差分、分流并在 `dwd_policy_analysis` 中保存为 `analysis_path='llm_diff'`。
*   人工检查 MySQL 表中记录，确保 `dwd_policy_sector_impact` 顺利从 Diff 结果中解析并继承了对应的利好行业记录。
