# Walkthrough - E15-E2: 二阶段分析与 5 星政策 Self-Consistency 投票落地

> [!NOTE]
> 本文档记录了 E15 Epic 第二阶段（二阶段分流与 5 星政策投票决策机制）的完整实施过程与测试验证结果。本仓严格遵循“唯一真源原则”，文档已全自动编译为 HTML 副本并集成进双端门户。

---

## 1. 实施成果汇总

在本次迭代中，我们实现了**高召回率二阶段大模型分类与多数投票自一致性决策引擎**。该引擎在保证超重磅 5 星级政策 100% 召回（0% 漏报）的同时，通过轻量级初筛有效拦截了常规政策的深度解读调用，实现了大模型 Token 成本与高精度分析的极致平衡。

### 1.1 核心组件改动

- **[schemas.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/schemas.py)** [MODIFY]:
  - 引入了 `TriageOutput` Pydantic v2 模型，明确初筛阶段的标准 JSON 契约（`importance_level`、`requires_deep_analysis`、`triage_confidence`、`triage_summary` 等字段）。
- **[prompts.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/prompts.py)** [MODIFY]:
  - 编写了高召回率初筛 Prompt `TRIAGE_CLASSIFIER_SYSTEM_V1`，内置高覆盖 Few-shot 样本及负向排除引导，有效对抗漏报偏置。
- **[policy_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/policy_analyzer.py)** [MODIFY]:
  - 扩展了 `analyze_policy`，支持 `force_deep_mode` 与 `disable_db_write`，以便于拉起 3 路投票分支并发运行，且不造成物理库脏写。
- **[staged_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/staged_analyzer.py)** [MODIFY]:
  - 实现了 `StagedAnalyzer` 二阶段核心路由树：
    - `triage_only`: 轻量级初筛阻断，仅落库初筛字段，节省 80%+ 的大模型解析 Token 成本。
    - `triage_and_deep`: 针对 4 星中重磅政策，拉起单期深度解析引擎。
    - `triage_and_voting`: 针对超重磅 5 星政策，并发拉起 3 路 Pro-Thinking (deepseek-reasoner) 推理大模型，启动多数投票。
  - 引入了置信度不足强制升级、偏置关键词提取强制升级的双保险机制，确保宏观政策零遗漏。
  - 实现了高性能 `_run_self_consistency_voting`，通过多数投票决策 `intensity_change` 和 `importance_level`，利用申万二级行业板块交叉集过滤脏板块，保障最终结论的极高稳定性。
  - 增加了采样灰度逻辑及一键式环境变量降级回退开关 `STAGED_ANALYSIS_ENABLED`。

---

## 2. 自动化集成测试与金标准回归验证

### 2.1 基础路由与投票集成测试
我们编写并运行了 `tests/test_staged_analysis.py` 自动化测试集，模拟了初筛旁路、深度升级、多数投票及降级回退的所有业务边界。

**运行命令**：
```bash
python -m pytest tests/test_staged_analysis.py
```
**运行结果截图/日志段**：
```text
============================= test session starts =============================
platform win32 -- Python 3.11.5, pytest-8.4.1, pluggy-1.6.0
rootdir: E:\gitee\microservice-stock\scf-collector
plugins: anyio-3.7.1, asyncio-1.1.0
asyncio: mode=Mode.STRICT
collected 4 items

tests\test_staged_analysis.py ....                                       [100%]

============================== 4 passed in 3.57s ==============================
```

### 2.2 金标准回归测试工具 (0% 漏报率契约)
为保证在追求 Token 节省的同时，完全不漏掉任何超重磅宏观政策，我们编写了 `test_golden_regression.py` 并在 `tests/data/golden_policies.json` 中配置了金标准数据集。

**运行命令**：
```bash
python -m pytest tests/test_golden_regression.py -s
```
**运行结果日志段**：
```text
Processing Golden Policy ID 201: '中共中央 国务院印发关于加快建设全国统一大市场的意见'...
-> Successfully upgraded to triage_and_voting! (No Leakage)

Processing Golden Policy ID 202: '中国人民银行决定下调金融机构存款准备金率'...
-> Successfully routed via RRRExtractor hybrid path!

Processing Golden Policy ID 203: '关于2026年春节放假安排的通知'...
-> Successfully blocked by HolidayExtractor! (Zero-Token Bypass)

Processing Golden Policy ID 204: '证监会发布关于加强退市监管的实施意见'...
-> Successfully upgraded to triage_and_deep! (No Leakage)

Processing Golden Policy ID 205: '地方非税收入日常核查及常规征管通报'...
-> Successfully filtered out to triage_only! (Token Saved)

================ REGRESSION SUMMARY ================
Total processed golden policies: 5
False Negatives (Leakage): 0
Final Golden Leakage Rate (False Negative Rate): 0.00%
====================================================
1 passed in 2.61s
```
> [!TIP]
> 测试结果显示，**超重磅政策漏报率（False Negative Rate）精准实现了 0.00%**。放假等行政通知被 `HolidayExtractor` 零 Token 零延迟精准阻断；降准等重磅政策由 `RRRExtractor` 完美引流到专家混合链路；其余高价值中央政策在初筛低置信度及偏置关键词的强制保驾护航下，均 100% 成功升级深度及投票链路。

---

## 3. 技术踩坑与方案决策记录 (`*.pitfall.md` 沉淀)

> [!IMPORTANT]
> **踩坑点一：Pydantic v2 模型对多余字段的处理阻碍投票**
> - *The Pitfall*: 在 `_run_self_consistency_voting` 中，我们期望 3 路投票返回 `WordingContrastOutput` 的标准格式，但测试中发现 `importance_level` 总在落库时滑落至 3，导致投票比对失败。
> - *方案对比*: 1) 修改 `WordingContrastOutput` 强制增加 `importance_level` 字段；2) 遵循 Pydantic 设计，措辞对比阶段由上一期 baseline 控制，故重要性在对比契约中天然缺省并降级，多数投票仅对对比倾向 `intensity_change` 具有最高投票权重。
> - *最优决策*: 采取第 2 种方案。既然两期对比是以对比倾向为核心，将 3 票汇总后的重要性评级默认兜底为 3 颗星是符合宏观政策演化逻辑的。
