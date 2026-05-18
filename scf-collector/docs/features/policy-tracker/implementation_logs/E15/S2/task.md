# Tasks - E15-E2: 二阶段分析与 5 星政策 Self-Consistency 投票落地

本任务清单用于追踪 E15 Epic 第二阶段（二阶段分流与 5 星政策投票决策机制）的工程落地进度。

- `[x]` [E15-E2-T1] **schemas.py**: 新增 `TriageOutput` Pydantic v2 模型，定义初筛分流的标准 JSON 契约。
- `[x]` [E15-E2-T2] **prompts.py**: 新增 `TRIAGE_CLASSIFIER_SYSTEM_V1` 静态系统 Prompt，内嵌多样本 Few-shot 及召回偏置关键词。
- `[x]` [E15-E2-T3] **policy_analyzer.py**: 为 `analyze_policy` 增加可选入参 `force_deep_mode` 与 `disable_db_write`，支持无数据库写入的纯 LLM 调用与板块融合计算。
- `[x]` [E15-E2-T4] **staged_analyzer.py**: 重构 `analyze_policy` 核心判定树，实现二阶段路由（triage_only / triage_and_deep / triage_and_voting）以及灰度采样和一键回滚开关。
- `[x]` [E15-E2-T5] **staged_analyzer.py**: 实现 `_run_self_consistency_voting` 进行 5 星政策多数投票，实现置信度熔断与投票高可用兜底。
- `[x]` [E15-E2-T6] **test_staged_analysis.py**: 编写 Given-When-Then 二阶段分析与 5 星投票自动化集成测试。
- `[x]` [E15-E2-T7] **test_golden_regression.py**: 编写金标准回归测试工具，验证高召回率要求。
- `[x]` [E15-E2-T8] **质量校验与交付**: 运行所有 pytest 测试，确保 100% 通过；全自动编译为 HTML，更新 docs 门户。
