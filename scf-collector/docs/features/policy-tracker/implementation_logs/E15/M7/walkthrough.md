# E15-M7: E6 增量(Diff)分析落地与集成交付报告

> [!NOTE]
> 本文档是 E15-M7 (E6-S2)「增量(Diff)分析落地与集成」的最终交付 Walkthrough 报告。记录了核心组件变更、单元与集成测试结果、以及宝贵的踩坑沉淀。

---

## 1. 核心变更摘要

针对宏观货政政策分析中“措辞微调极难捕捉且大模型分析重复费用高”的问题，我们成功落地并集成了 **E6 增量(Diff)分析引擎**，实现对高度相似 4 星政策的自动差分与高密度措辞变化提取。

### 1.1 新增与修改模块

1. **新增 [diff_helper.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/diff_helper.py)**
   - 实现了高精度的句子清理与切片算法 (`clean_lines`)，支持按句号、分号及换行符多重切割并剔除空白。
   - 封装了增量提取逻辑 (`generate_text_diff`)，基于 `difflib.unified_diff(n=1)` 算法，仅捕获并输出发生改动的行（带有 `+` 或 `-` 前缀），剔除冗余头部信息，实现大模型 Token 的极大节省。

2. **升级 [prompts.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/prompts.py)**
   - 注入了缓存高度友好的 `WORDING_DIFF_SYSTEM_V1` 系统提示词。
   - 该提示词专为 DeepSeek 缓存命中优化，静态系统 prompt 保持完全一致，通过 User Prompt 输入由 `diff_helper` 处理后的增量 diff 段落，引导大模型进行高精度的“措辞边际变化、倾向性倾向改变、利好行业”分析。

3. **集成二阶段路由分流 [staged_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/staged_analyzer.py)**
   - 增加了 `DIFF_ANALYSIS_ENABLED` 环境变量管控（默认 `true`）。
   - 在一阶段 triage 初筛之后，拦截 4 星政策，若相似度检测结果为 `high`（汉明距离 <= 3），则自动转为 `triage_and_diff` 升级路径。
   - 桥接上一期分析的 DWD 明细，提取 `summary` 和 `segment_used`，利用 `diff_helper` 进行句级差分，并以 `force_deep_mode='diff_only'` 调起二阶段深度分析。

4. **桥接与数据硬化 [policy_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/policy_analyzer.py)**
   - 升级支持 `force_deep_mode='diff_only'` 比对模式。在此模式下，自动绕过前置基准提取，采用 `WordingContrastOutput` 做强 Schema 约束校验。
   - **防降级契约保障**：针对 `WordingContrastOutput` Schema 没有 `importance_level` 字段的设计漏洞，自动通过路径识别与 triage 继承机制进行动态回补（默认回补为符合分流约定的 `4` 星），确保数据在 `dwd_policy_analysis` 中落库时的绝对完整性。
   - 移除所有局部导入，确保全局数据库适配器可以被 `unittest.mock` 完美代理拦截。

---

## 2. 自动化测试与验证

我们编写了全覆盖的 pytest 单元与集成测试用例 [test_m7_features.py](file:///e:/gitee/microservice-stock/scf-collector/tests/test_m7_features.py)，用例结构严格遵循 Given-When-Then 设计模式：

1. `test_diff_helper_clean_lines`：验证句子精细切片与前后空白剔除。
2. `test_diff_helper_generate_text_diff`：验证 Unified Diff 在保留增量信息的同时剔除了元数据头部。
3. `test_staged_analyzer_diff_route_four_star`：模拟完整的 4 星高度相似 LPR 政策初筛、差分、LLM 调用与 DWD 落库链路（验证 `analysis_path='llm_diff'` 和 `routing_path='triage_and_diff'`）。
4. `test_staged_analyzer_diff_exempt_five_star`：验证 5 星特大重磅公告（如特大货政降准报告）即使相似度为 `high` 也强制豁免 Diff 路径，确保 100% 进入 3次 Pro-thinking 多数投票的 `triage_and_voting` 深度路径。

### 2.1 测试运行输出

测试用例 100% 通过，没有任何 localhost 连接超时或 unbound local 杂音：

```bash
python -m pytest tests/test_m7_features.py -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.11.5, pytest-8.4.1, pluggy-1.6.0 -- D:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: E:\gitee\microservice-stock\scf-collector
plugins: anyio-3.7.1, asyncio-1.1.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 4 items

tests/test_m7_features.py::test_diff_helper_clean_lines PASSED           [ 25%]
tests/test_m7_features.py::test_diff_helper_generate_text_diff PASSED    [ 50%]
tests/test_m7_features.py::test_staged_analyzer_diff_route_four_star PASSED [ 75%]
tests/test_m7_features.py::test_staged_analyzer_diff_exempt_five_star PASSED [100%]

============================== 4 passed in 1.63s ==============================
```

---

## 3. 避坑与技术秘籍记录 (Story Pitfall & Tech Tips)

在开发与测试过程中，我们遇到了两个非常隐蔽且致命的技术反模式，并探索出了最合理的择优方案。

### 3.1 踩坑记录 (The Pitfalls)

> [!WARNING]
> **坑 1：异步调度器中的局部/隐式导入导致单元测试 mock 穿透**
> - **问题现象**：在测试用例中，我们使用 `@patch("shared.utils.staged_analyzer.execute_query")` 对数据库方法进行了 mock。但在运行测试时，程序仍然疯狂尝试连接 `localhost:3306` 并因为 3 次重试失败而耗时超长或崩溃。
> - **问题根源**：`staged_analyzer.py` 的方法内部存在 `from shared.db.connection import execute_query` 这种**局部导入**。在测试收集阶段，局部导入由于未执行，因此没有被 patch；一旦在运行时被执行，局部导入会直接从 `shared.db.connection` 读取原始的、未被 mock 污染的方法，从而彻底击穿了单元测试沙箱。
> - **择优决策**：废除所有局部隐式导入，将 `execute_query` 的导入全部收拢到模块级（顶层文件导入），并在测试用例中分别对 `shared.utils.staged_analyzer.execute_query` 和 `shared.utils.policy_analyzer.execute_query`进行模块命名空间级的 patch，杜绝任何物理击穿。

> [!WARNING]
> **坑 2：WordingContrastOutput 强 Pydantic 校验与 DWD 物理表星级必填契约之间的空值落空**
> - **问题现象**：增量差分模式下的 JSON 骨架由 `WordingContrastOutput` 提供（该 Schema 无 `importance_level` 星级字段），而落库数据库 `dwd_policy_analysis` 的 `importance_level` 却是一个必填的整型契约字段。大模型在返回 JSON 时不包含重要性星级，如果默认解析返回 `None` 或退化为 `3`，将直接破坏 triage 初筛做出的 `4` 星评估，导致前后星级冲突。
> - **择优决策**：在 `policy_analyzer.py` 数据融合落库前（第 412 行），增加动态的 fallback 判定：
>   ```python
>   importance_level = analysis_data.get("importance_level")
>   if importance_level is None:
>       importance_level = 4 if (force_deep_mode == 'diff_only' or analysis_path == 'llm_diff') else 3
>   ```
>   这既保证了 `diff_only` 路径无感完美继承星级，又防止了字段空值导致的数据契约崩溃。

### 3.2 复用技巧 (Reusable Tips)

> [!TIP]
> **AI 友好测试桩设计：**
> 在为异步微服务编写 DB 测试时，不需要每次都编写复杂的 mock 实例。使用 `side_effect` 针对 SQL 字符串关键字进行动态分支匹配（如匹配 `SELECT summary` 与 `INSERT INTO`），即可用最少、最干净的行数模拟复杂的数据库多级事务。
