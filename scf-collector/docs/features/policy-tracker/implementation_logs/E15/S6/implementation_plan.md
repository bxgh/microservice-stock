# Implementation Plan - E15-E6-S1: 政策相似度检测 (SimHash & Hamming Distance)

本方案针对 AI 政策分析引擎中的 E6-S1 阶段（政策相似度检测）开展详细的设计与实施规划。本阶段的核心目标是通过基于核心段落（`segment_used`）的 SimHash（64位）与汉明距离算法，精确识别高相似度的连续政策。这为后续 E6-S2 的增量（Diff）分析与 Token 极致压缩奠定坚实的确定性基础。

---

## 需求解析与核心逻辑 (3句话)

1. **核心段落 SimHash 计算**：对于所有流入的政策，在大模型调用前，提取其经过结构化切片后的核心段落（`segment_used`），采用纯 Python、无三方依赖、100% 平台兼容 of 64 位 SimHash 算法计算其文本指纹。
2. **汉明距离比对与分类**：在入库和分析分流阶段，异步检索相同发文机构（`ts_code`）和相同细分类别（`policy_type`）的历史最新分析记录，计算两期核心段落的汉明距离（Hamming Distance），判定相似度等级（高度相似 $\le 3$、中度相似 $4\text{-}8$、常规相似 $> 8$）。
3. **入库与分析路由扩展**：在 `dwd_policy_analysis` 表中将 `core_segment_simhash`（16位十六进制 `CHAR(16)`）字段落库；在 `StagedAnalyzer` 决策树中注入“相似度检测分流点”，对高度相似政策打上标记，为 E6-S2 的 Diff 增量大模型调用提供完美的触发机制。

---

## 激活角色说明

*   `[Macro Policy Architect] (宏观政策架构师)`：负责统筹分流路由设计，确保增量（Diff）旁路在不破坏现有 staged 分析流的前提下平滑嵌入。
*   `[Data Integrity Steward] (数据质量掌门人)`：负责 SimHash 文本指纹分词强度、散列碰撞率审计，以及判定阈值（$\le 3$ 与 $4\text{-}8$）的金融语义准确性验证。
*   `[Senior Python Backend Engineer] (资深异步后端工程师)`：负责高效编写纯 Python 64 位 SimHash 算法（避免 SCF 打包 `.pyd` 二进制二进制冲突），优化数据库异步检索性能，防范重试时的数据幂等问题。

---

## User Review Required

> [!IMPORTANT]
> **1. 纯 Python 零依赖 SimHash 设计**
> *   **红线避坑**：为了 100% 确保腾讯云 SCF（Serverless）运行环境兼容性，杜绝任何 `.pyd` 跨平台二进制依赖审查报错，本方案**强行废弃** C 语言编译的 `simhash` pip 依赖，转为使用基于 Python 标准库 `hashlib` 和 `re` 构建的高性能纯 Python `SimHash` 算法。
> 
> **2. 相似度计算对象约束：仅对核心段落（`segment_used`）计算**
> *   **去套话稀释**：政府及央行政策包含大量“开头致辞、印发文号、附件说明、抄送机关”等套话（占比常达 30%-50%）。如果对全文计算 SimHash，套话的微小日期或文号变动会主导哈希值，导致汉明距离严重失真（例如：内容相同的 LPR，仅日期不同，全文汉明距离可能 $> 10$）。本方案强制在 `segment_used`（已过滤的纯核心段落）上计算哈希，确保高度相似政策汉明距离稳定在 $\le 2$。
> 
> **3. 阈值设定依据**
> *   **汉明距离 $\le 3$**：代表 64 位哈希中只有不超过 3 个 bit 不同，语义极度重合（数字变动或个别字词增删），完美适配 E6-S2 的 Diff 路径。
> *   **汉明距离 $4\text{-}8$**：代表中度相似，有段落微调，记录提示但走完整路径。
> *   **汉明距离 $> 8$**：无相似性，常规处理。

---

## Open Questions

> [!NOTE]
> **Q1: 规则路径提取（Rule-Based Bypass）的政策是否需要计算 SimHash？**
> *   **决策**：是的。虽然规则路径（如 LPR/OMO/MLF）完全绕过了大模型调用（Token 消耗本就为 0），但为了保持 DWD 数据表 `core_segment_simhash` 字段的完整可审计性，以及未来数据统计的统一性，规则提取器也应该在落库时计算并写入 `core_segment_simhash`。

---

## Proposed Changes

### Component: Similarity & Hash Utilities

---

#### [NEW] [simhash.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/simhash.py)
*   **修改内容**：实现纯 Python 64位 SimHash 文本指纹计算器与汉明距离计算函数。
*   **核心逻辑**：
    1. 使用正则 `re.findall` 将中文汉字、英文单词 and 数字切分为 tokens。
    2. 使用 `hashlib.md5` 产生 128 位哈希，截取前 8 字节（64位）作为特征哈希值。
    3. 构建 64 维特征权重向量，累加特征权重。
    4. 将大于等于 0 的维度置 1，小于 0 的置 0，生成 64 位整数，格式化输出为 16 位十六进制小写字符串（`CHAR(16)`）。
    5. 实现 `hamming_distance` 利用位运算快速计算异或 bit 数。

---

### Component: Policy Ingestion & Analysis Dispatcher

---

#### [MODIFY] [policy_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/policy_analyzer.py)
*   **修改内容**：
    1. 引入 `shared.utils.simhash.compute_simhash`。
    2. 在 `analyze_policy` 流程中，在提取出 `segment_used` 后，立刻计算其 simhash:
       ```python
       core_segment_simhash = compute_simhash(segment_used)
       ```
    3. 将 `core_segment_simhash` 写入 `sql_analysis` 的 `INSERT` 和 `ON DUPLICATE KEY UPDATE` 子句，并将其作为参数传入。
    4. 确保返回的字典中包含 `core_segment_simhash`。

---

#### [MODIFY] [staged_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/staged_analyzer.py)
*   **修改内容**：
    1. 引入 `compute_simhash` 和 `hamming_distance`。
    2. 新增异步方法 `find_similar_previous_policy`，用于在 `dwd_policy_analysis` 中查找同 `ts_code` 和 `policy_type` 的历史最相似记录。
    3. 在 `analyze_policy` 调度入口中：
       *   规则未命中时，计算当前政策的 `core_segment_simhash`。
       *   在进入 LLM 初筛/深度分析前，调用 `find_similar_previous_policy` 获取最相似历史政策及汉明距离。
       *   将相似度比对结果（汉明距离、最相似政策 ID、相似度评级）记录到日志中，并暂时注入返回字典中。
       *   若汉明距离 $\le 3$，打印高亮日志 `"[Similarity Alert] Highly similar policy detected! Distance: X. Candidate for E6-S2 Diff Route."`。
    4. 在 `_write_rule_result_to_db` 和 `_write_triage_to_db` 中，也同步计算并落库 `core_segment_simhash`。

---

## AI 实施蓝图与提示词 (Plan-as-Prompt)

> [!IMPORTANT]
> **Subagent 执行指南 (必读)**
> 1. **零二进制依赖**：`simhash.py` 中绝对不允许导入第三方编译包，完全使用 `hashlib` 及 Python 内置算术运算符，确保其在 Windows 开发环境和 Linux SCF 生产环境中行为完全一致。
> 2. **健壮 of Tokenizer**：在 `compute_simhash` 中对中文分词做防空容错，如果正则未能分出任何 token，使用原文本作为唯一 token 兜底，防止 `ZeroDivisionError`。
> 3. **SQL 参数对齐**：更新 `policy_analyzer.py` and `staged_analyzer.py` 的 SQL INSERT 时，务必严格对齐字段顺序和 `params_analysis` 占位符元组，防止 `Column count doesn't match value count` 错误。
> 4. **HTML 全自动编译**：完成开发和回归后，必须运行 `python scripts/md_to_html_premium.py` 将生成的 `walkthrough.md` 及相关文档编译为 HTML。

---

## Verification Plan

### Automated Tests
*   **单元测试 `test_simhash.py`**：
    *   AC1 验证：构造两份仅日期和个别数字不同的 LPR 文本（如“2026年5月20日贷款市场报价利率为3.0%”与“2026年6月20日贷款市场报价利率为3.1%”），验证核心段落的汉明距离 $\le 2$。
    *   防幻觉验证：构造两份完全不同的公告（人事任命 vs 逆回购），验证汉明距离 $> 10$。
    *   边界测试：空文本、特殊字符文本、极短文本测试，确保不抛出异常。
*   **集成测试 `test_similarity_detection.py`**：
    *   Mock 数据库中的历史 `dwd_policy_analysis` 数据。
    *   调用 `staged_analyzer.find_similar_previous_policy`，验证能够正确捞出相似政策，计算出符合预期的汉明距离，并正确标记分流状态。

### Manual Verification
*   在 `sandbox` 环境中插入一条 LPR 历史记录，随后模拟发送一条新一期 LPR。
*   执行 `StagedAnalyzer.analyze_policy`，观察终端输出的 CLS 结构化日志与相似度判定日志，确保完美识别出高相似度。
*   直连 MySQL 数据库，查询 `SELECT id, policy_id, core_segment_simhash FROM dwd_policy_analysis ORDER BY id DESC LIMIT 2`，确认 simhash 字段被正确填充为 16 位十六进制且不为 NULL。
