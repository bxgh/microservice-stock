# E15-S1 迭代纪要 (v2: M1-Patch 深度补漏与防裸奔加固)

## 1. 迭代触发动因 (Trigger)
在 M1 第一阶段（规则 Bypass 与 Caching 基础架构）代码交付后，经架构侧深度审计，判定原方案处于“伪完成”状态，存在直接切主流量污染数据、缓存前缀失锁等“裸奔”风险。本次 v2 迭代旨在修补以下关键防线：
- **P0 风险闭环**：缺失影子双跑模式（全量上线规则极易因边界 case 污染 `dwd_policy_analysis` 主表）。
- **P0 盲盒化规避**：缺失 Prefix-Freeze 字节级 MD5 一致性监控，若混入动态参数将导致命中率暗跌；缺失 60% 阈值熔断邮件告警。
- **P1 逻辑调优**：5星级存款准备金率 (RRR) 政策纯规则提取过于生硬，亟需转型为 `rule_then_llm` 混合路径；缺失错峰时段 50% 折扣的物理测算兜底。

## 2. 影响面评估 (Impact Map)
- **数据库拓展**: 新建 `dwd_policy_analysis_shadow` 表（与主表 100% 结构一致），专门承载 shadow 模式下的验证写流。
- **分析引擎调优**: `staged_analyzer.py` 新增 `RULE_BASED_PATH_ENABLED` 环境变量双路开关，新增 `bypass_failed=1` 优雅回退流转机制。
- **大模型调用端**: 补齐跨调用的 `raw_request_system_prompt` 哈希校验监控脚本。

## 3. 回归验证清单 (Regression AC)

### 3.1 代码交付
- [ ] V1.9 迁移：物理建表 `dwd_policy_analysis_shadow` 完毕。
- [ ] 5 个提取器全部启用 VERSION 控制，RRR 及 Holiday 完成防漏/避让加厚。

### 3.2 集成验证 (P0 必补)
- [ ] System prompt 字节一致性测试通过（证明 `MD5(raw_request_system_prompt)` 跨调用一致无动态参数）。
- [ ] `LLMClient` 首次预热 + 连续调用测试，证明物理 `prompt_cache_hit_tokens > 0`。
- [ ] Extractor fallback 路径单元测试通过（验证缺损数据引发 `bypass_failed=1` 并自动回退 LLM）。
- [ ] 调度器双路并行影子模式全量就绪（环境变量随时可启停 `shadow|production|disabled`）。

### 3.3 生产监控 (P0 必补)
- [ ] 编写缓存命中率实时统计 SQL 监控探针。
- [ ] 确立 P1 级邮件告警机制代码（命中率连续 3 小时 < 60% 触发）。
- [ ] 测实验证 `is_off_peak` 字段写入正常，日累计表可分片聚合。

### 3.4 实测校准 (P1 应补)
- [ ] 开发并运行 `scratch/test_off_peak_discount.py`，查明真实扣费的官方折扣比例。
- [ ] RRR 测试用例走 `rule_then_llm`，确保板块解析逻辑受大模型专家校准。
- [ ] Holiday 白噪音测试涵盖带“操作/利率/准备金”等词的实质政策，确保不被错误拦截。

---
*注：本迭代完结前，M1 阶段不宣告“完成”，以真实数据防线为准。*
