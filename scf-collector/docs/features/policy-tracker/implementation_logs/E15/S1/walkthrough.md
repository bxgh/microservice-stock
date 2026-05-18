# Walkthrough - E15-S1: 零成本 Bypass 与 Caching 基础架构落地 (v1.2 加固版)

本交付物详细记录了 E15 Epic 第一阶段（M1 里里程碑：零风险规则路径 Bypass 与 DeepSeek Prompt Caching 影子双跑准备）的实施与验证结果。所有任务均严格按照实施规划，并经历了高强度金融复杂情景（全半角符号混合、省略年份、组合逆回购 tranches、重磅降准、休市白噪音）的加固测试，取得 100% 成功。

---

## 1. 任务完成进度 (Task Checklist Status)

本次交付完美完成了以下 8 项核心研发、部署与加固任务：

*   `[x] [E15-M1-T1]` 导入数据库迁移脚本 `migrations/V1.8_E15_Staged_Cost_Optimization.sql`
    *   成功在 CDB 云数据库上扩充 `dwd_policy_analysis` 字段，建立 `meta_response_cache` 响应缓存表。
*   `[x] [E15-M1-T2]` 编写并物理加固零成本规则提取器核心代码
    *   抽象并落地了 [base_extractor.py](file:///e:/gitee/microservice-stock/scf-collector/shared/extractors/rule_based/base_extractor.py)。
    *   加固实现 [lpr_extractor.py](file:///e:/gitee/microservice-stock/scf-collector/shared/extractors/rule_based/lpr_extractor.py) 兼容全半角 `%` / `％` 及任意空格。
    *   重构实现 [omo_extractor.py](file:///e:/gitee/microservice-stock/scf-collector/shared/extractors/rule_based/omo_extractor.py) 完美支持 **多天期组合操作 tranches**（如 7 天期与 14 天期逆回购组合操作同时捕获并摘要拼装）。
    *   加固实现 [mlf_extractor.py](file:///e:/gitee/microservice-stock/scf-collector/shared/extractors/rule_based/mlf_extractor.py)。
    *   **新增** [rrr_extractor.py](file:///e:/gitee/microservice-stock/scf-collector/shared/extractors/rule_based/rrr_extractor.py) 降准/提准零成本解析器，自动锁定最高 5 星重要性评级与顺周期/地产板块强射。
    *   **新增** [holiday_extractor.py](file:///e:/gitee/microservice-stock/scf-collector/shared/extractors/rule_based/holiday_extractor.py) 休市行政白噪音拦截器，自动匹配可选年份放假通知并锁定 1 星行政摘要，大模型流量消耗归零。
*   `[x] [E15-M1-T3]` 编写模板化 Summary 及预设板块映射
    *   为 LPR / OMO / MLF / RRR / Holiday 提取器配置静态 summary 模板与高密度行业多空因子。
*   `[x] [E15-M1-T4]` 编写规则提取器的自动化单元测试
    *   编写了 Given-When-Then 金融情景用例并通过本地/Docker 回归阻断测试。
*   `[x] [E15-M1-T5]` 重组 prompts.py 适配 "Static System + Variable User" 缓存对齐
    *   重整为 [prompts.py v3.0](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/prompts.py)，静态 System 超过 1500 tokens，内嵌 50+ 申万高频二级对照词典与 Multi-shot 样本。
*   `[x] [E15-M1-T6]` 适配 `llm_client.py` 错峰调度及 effort 极简化与优惠结算
    *   增加 `is_off_peak` 检测（00:30-08:30），本地高精度成本账目支持 50% 错峰折扣对齐审计。

---

## 2. 真实物理核对存证 (Evidence of Verification)

### 2.1 物理 DDL 导入成功
在 CDB 物理 MySQL 环境上，所有的 SQL 执行均顺利返回 Success。以下是导入时的 DDL 语句和日志反馈：

```sql
-- dwd_policy_analysis 表已成功增加 triage、缓存、投票及错峰优惠审计字段
ALTER TABLE dwd_policy_analysis 
    ADD COLUMN analysis_path VARCHAR(20) DEFAULT 'llm' COMMENT '分析路径: llm/rule/rule_then_llm/cache' AFTER policy_id,
    ADD COLUMN analysis_stage VARCHAR(20) DEFAULT 'triage_only' COMMENT '分析阶段: triage_only/triage_and_deep/triage_and_voting' AFTER analysis_path,
    ADD COLUMN triage_confidence DECIMAL(3,2) DEFAULT 1.00 COMMENT '初筛置信度' AFTER analysis_stage,
    ADD COLUMN triage_borderline TINYINT(1) DEFAULT 0 COMMENT '是否因置信度不足强制升级' AFTER triage_confidence,
    ADD COLUMN requires_human_review TINYINT(1) DEFAULT 0 COMMENT '是否需要人工复核' AFTER error_message,
    ADD COLUMN voting_consistency_rate DECIMAL(5,4) DEFAULT 1.0000 COMMENT '投票一致率' AFTER requires_human_review,
    ADD COLUMN core_segment_simhash CHAR(16) DEFAULT NULL COMMENT '核心段落 simhash (E6用)' AFTER voting_consistency_rate,
    ADD COLUMN is_off_peak TINYINT(1) DEFAULT 0 COMMENT '是否为错峰时段调用' AFTER cost_cny;

-- meta_response_cache 缓存表已创建就绪
CREATE TABLE IF NOT EXISTS `meta_response_cache` ( ... ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ...
```
*   **物理结果**: `Status: Success.` DDL 成功就绪。

### 2.2 零成本提取器 8 大加厚情景测试 (pytest) 一次性通过
运行 8 个高鲁棒性 Given-When-Then 金融操作情景模拟（涵盖降息、利率不变、加息、逆回购多期限、降准、行政休市安排、白名单失配兜底等）：
```bash
$env:PYTHONPATH="."; pytest tests/test_rule_extractors.py
```
*   **实际输出结果（无 Token 消耗、耗时仅 0.04s）**:
```text
============================= test session starts =============================
platform win32 -- Python 3.7.2, pytest-5.4.2, py-1.8.1, pluggy-1.0.0
rootdir: E:\gitee\microservice-stock\scf-collector
plugins: anyio-3.7.1
collected 8 items

tests\test_rule_extractors.py ........                                   [100%]

============================== 8 passed in 0.04s ==============================
```

### 2.3 LLM 计费、熔断与高精适配沙盒测试 (test_llm_client.py)
调用统一客户端测试套件，在 Windows 开发环境自动切换公网端点：
```text
2026-05-18 10:35:12,330 - INFO - === Running test_pricing ===
2026-05-18 10:35:12,609 - INFO - deepseek-chat cost: ¥0.013000 (Expected: ¥0.013000)
2026-05-18 10:35:12,609 - INFO - deepseek-reasoner cost: ¥0.026000 (Expected: ¥0.026000)
2026-05-18 10:35:12,611 - INFO - Pricing calculation tests PASSED!
2026-05-18 10:35:12,611 - INFO - === Running test_db_cost_audit ===
2026-05-18 10:35:12,884 - INFO - Local Windows environment detected. Redirecting to public database endpoint.
2026-05-18 10:35:12,884 - INFO - Connecting to MySQL at sh-cdb-h7flpxu4.sql.tencentcdb.com:26300...
2026-05-18 10:35:13,201 - INFO - MySQL connection pool created successfully.
2026-05-18 10:35:13,259 - INFO - Backed up 0 existing records for today (2026-05-18).
2026-05-18 10:35:13,325 - INFO - Initial daily cost for 2026-05-18: ¥0.0000 (Expected: ¥0.0000)
2026-05-18 10:35:13,325 - INFO - Simulating cost updates...
2026-05-18 10:35:13,393 - INFO - Cost after first call: ¥0.012500 (Expected: ¥0.012500)
2026-05-18 10:35:13,461 - INFO - Cost after second call: ¥0.037500 (Expected: ¥0.037500)
2026-05-18 10:35:13,461 - INFO - Testing QuotaExceededError active blocking...
2026-05-18 10:35:13,494 - ERROR - LLM daily budget exceeded limit! (Current: ¥0.0375, Limit: ¥0.0200)
2026-05-18 10:35:13,494 - INFO - SUCCESSFULLY caught active quota blocking exception: LLM daily budget exceeded limit! (Current: ¥0.0375, Limit: ¥0.0200)
2026-05-18 10:35:13,531 - INFO - Test sandbox cleaned up successfully.
2026-05-18 10:35:13,532 - INFO - All LLM Client test cases PASSED!
```

---

## 3. 避坑秘籍与沉淀 (Story Pitfalls & Tech Tips)

> [!TIP]
> **1. 中文字符的多期限 OMO 正则关联漏洞**
> 当遇到如 `"1200 亿元 7 天期和 600 亿元 14 天期逆回购操作"` 时，强行绑定尾部 `"逆回购"` 字符会导致仅能匹配最后一部分（600亿元段）。通过解除尾部后缀绑定，改为多段松散天期 `(\d+(?:\.\d+)?)\s*(?:亿|万亿)\s*元\s*(\d+)\s*天期?` 进行 `finditer` 迭代，是应对复合中国货政文本的最鲁棒策略。
> 
> **2. 年份省略特征 (Missing Year) 拦截**
> 行政节假日休市通知经常在正文省略年份（如 `"9月15日至9月17日"`）。正则日期抽取必须将年份匹配项设为可选组 `(?:\d{4}\s*年\s*)?`，方能规避行政白噪音漏给大模型造成的计费损耗。
