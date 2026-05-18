# Task List - E15-E6-S1: 政策相似度检测 (SimHash & Hamming Distance)

## ── E6-S1: SimHash 核心算法与数据库改造 ──

- [x] `[E15-E6-S1-T1]` 实现纯 Python 64位 SimHash 算法与汉明距离计算 ([simhash.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/simhash.py))
- [x] `[E15-E6-S1-T2]` 修改 [policy_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/policy_analyzer.py) 使得入库时计算并写入 `core_segment_simhash`
- [x] `[E15-E6-S1-T3]` 修改 [staged_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/staged_analyzer.py) 使得规则阻断与 triage_only 路由也同步落库 `core_segment_simhash`

## ── E6-S1: 近似政策检测分流 ──

- [x] `[E15-E6-S1-T4]` 在 [staged_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/staged_analyzer.py) 中实现 `find_similar_previous_policy` 异步相似历史查找函数与日志分流点
- [x] `[E15-E6-S1-T5]` 编写单元测试 [test_simhash.py](file:///e:/gitee/microservice-stock/scf-collector/tests/test_simhash.py) 与集成测试 [test_similarity_detection.py](file:///e:/gitee/microservice-stock/scf-collector/tests/test_similarity_detection.py)

## ── E6-S1: 质量验收与交付 ──

- [x] `[E15-E6-S1-T6]` 运行全量单元测试与集成测试，验证相似度检测的汉明距离阈值判定正确
- [x] `[E15-E6-S1-T7]` 编写 `walkthrough.md`，执行 HTML 自动编译，更新全局 Portal 门户索引
