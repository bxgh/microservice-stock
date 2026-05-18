# Task List - E15: AI 政策分析引擎效率与成本优化 M1 阶段实施清单 (v1.1)

## ── E1: 规则零成本路径 (Rule-Based Bypass) ──

- [x] `[E15-M1-T1]` 导入数据库迁移脚本 `migrations/V1.8_E15_Staged_Cost_Optimization.sql`
    - [x] 编写 MySQL 5.7 兼容的扩展 SQL DDL。
    - [x] 执行数据库迁移并核实 `dwd_policy_analysis` 表及 `meta_response_cache` 表字段结构。
- [x] `[E15-M1-T2]` 编写零成本规则提取器核心代码
    - [x] 创建 `scf-collector/shared/extractors/rule_based/` 目录。
    - [x] 实现 `base_extractor.py` 抽象类，声明标准化接口。
    - [x] 实现 `lpr_extractor.py`（精确匹配 1Y/5Y 利率、生效日期、数字 diff 涨跌基点）。
    - [x] 实现 `omo_extractor.py`（OMO 逆回购操作金额、期限、利率）。
    - [x] 实现 `mlf_extractor.py` / `slf_extractor.py`（中期借贷及常备借贷便利提取）。
- [x] `[E15-M1-T3]` 编写模板化 Summary 及预设板块映射
    - [x] 为 LPR / OMO / MLF 提取器配置静态 summary 模板。
    - [x] 注入 sectors_positive/negative 预设映射（如 LPR 下调 -> 银行偏空、地产偏多，OMO 变动 -> 证券利好）。
- [x] `[E15-M1-T4]` 编写规则提取器的自动化单元测试
    - [x] 新建 `scf-collector/tests/test_rule_extractors.py`。
    - [x] 编写 Given-When-Then 用例，模拟 LPR、OMO 提取成功（AC1）及格式异常回退 (AC2)。
    - [x] 运行测试验证，确保零 token 消耗（AC3）。

## ── E3 & E4: Prompt 重组与 Prefix-Freeze 影子模式就绪 ──

- [x] `[E15-M1-T5]` 重组 prompts.py 适配 "Static System + Variable User" 缓存对齐
    - [x] 修改 `scf-collector/shared/utils/prompts.py`。
    - [x] 将 system prompt、few-shot 样本、申万对照词典完全冻结置入 System Message，长度垫厚至 1000 tokens 以上以最大化一折缓存绝对收益。
    - [x] 将动态政策内容隔离至 User Message 尾部注入。
- [x] `[E15-M1-T6]` 适配 `llm_client.py` 错峰调度及 effort 极简化与优惠结算
    - [x] 调整大模型调用参数，支持 output schema 极简化（移除冗余字段，约束 summary 每句 ≤ 40字）。
    - [x] 为 V4 注入 `is_off_peak` 并检测 `reasoning_tokens` 审计流。
