# Task Checklist - E15-M7: E6 增量(Diff)分析落地与集成

- `[x]` **E6-S2 Diff 提取算法与 Prompt 注入**
    - `[x]` 新建 `scf-collector/shared/utils/diff_helper.py` (句子级分词/清理与 unified_diff n=1 控制)
    - `[x]` 升级 `scf-collector/shared/utils/prompts.py` 添加 `WORDING_DIFF_SYSTEM_V1` 静态缓存友好 Prompt
- `[x]` **二阶段路由分流与分析器桥接**
    - `[x]` 升级 `scf-collector/shared/utils/staged_analyzer.py` 支持 `DIFF_ANALYSIS_ENABLED` 并集成高度相似 4星 政策的 Diff 重定向
    - `[x]` 升级 `scf-collector/shared/utils/policy_analyzer.py` 支持 `force_deep_mode='diff_only'` 边际对比模式
- `[ ]` **系统集成测试与验证**
    - `[ ]` 编写 `scf-collector/tests/test_m7_features.py` 全方位 Given-When-Then 单元/集成测试
    - `[ ]` 物理运行 pytest 测试并验证 100% 通过
    - `[ ]` 产出 `walkthrough.md` 交付报告与 `walkthrough.html` 副本，并刷新文档门户
