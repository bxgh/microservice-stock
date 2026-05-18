# M1-Patch 深度补漏验收清单看板

## 代码交付
- `[x]` V1.9 迁移：物理建表 `dwd_policy_analysis_shadow` 完毕。
- `[x]` 5 个提取器全部启用 VERSION 控制，RRR 降准转混合路径及 Holiday 白名单防漏。

## 集成验证 (P0 必补)
- `[x]` 编写验证脚本 `verify_prompt_consistency.py` 并通过字节一致性测试（MD5 跨调用绝对一致）。
- `[x]` 验证 LLMClient 首次预热 + 连续调用，测试 `prompt_cache_hit_tokens > 0`。
- `[x]` Extractor fallback 路径单元测试通过（缺损数据可退流 LLM）。
- `[x]` 调度器双路并行影子模式全量就绪（环境变量 `shadow|production|disabled` 自由切换）。

## 生产监控 (P0 必补)
- `[x]` 编写缓存命中率实时统计 SQL 监控探针。
- `[x]` 确立 P1 级邮件告警机制代码（命中率连续 3 小时 < 60% 触发）。
- `[x]` 测实验证 `is_off_peak` 字段写入正常，日累计表可分片聚合。

## 实测校准 (P1 应补)
- `[x]` 编写 `scratch/test_off_peak_discount.py`，物理确认 50% 错峰折扣是否精准。
- `[x]` 测试 RRR `rule_then_llm` 混合路径.
- `[x]` Holiday 白噪音“政策操作”避让词防御测试。
