# E14-S2 Phase 4: 全量历史回填与 CLS 可观测性 (物理设计书)

本阶段聚焦于灰度及近一周历史回填脚本、高容错断点续传设计、硬防线预算控制以及全面上线前的单元/集成测试。

## 1. 历史回填脚本设计 (backfill_policy_analysis.py)
在 `scripts/backfill_policy_analysis.py` 中编写离线处理脚本。
- **近一周数据回填策略**：
  为确保不超支，且仅校验近期政策，回填脚本将物理范围限制在 **“最近 7 天内”** 发布的数据：
  ```sql
  -- 扫描当前库中近一周内未被 AI 分析的政策数据
  SELECT ods.*
  FROM ods_policy_info ods
  LEFT JOIN dwd_policy_analysis dwd 
    ON ods.id = dwd.policy_id 
   AND dwd.prompt_name = 'general_summary' 
   AND dwd.prompt_version = 'v2'
  WHERE dwd.id IS NULL
    AND ods.publish_date >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
    AND ods.is_deleted = 0
  ORDER BY ods.publish_date DESC;
  ```
- **批次与速率控制**：以每批 50 条为单位进行处理（最近一周政策实际通常少于 10 条，单批次即可跑完）。每次调用完毕后，调用 `time.sleep(1.0)` 防火墙式防御大模型接口 429 报错。
- **¥1元 硬防线预算控制**：
  - 维护一个全局内存变量 `accumulated_cost`；
  - 每次大模型调用完毕，解析 token 返回值并依据单价表公式实时累加；
  - 一旦 `accumulated_cost >= 50.0`，立即优雅挂起，保存进度并控制台输出：`[CRITICAL] 历史回填已达预设 ¥50 元预算防线，脚本主动安全挂起。`

---

## 2. 单元与集成测试用例 (Given-When-Then)
在 `tests/test_policy_analyzer.py` 中：

### 2.1 测试案例一：通用摘要解析与板块融合测试
- **Given**: 输入一篇 CSRC 板块政策原文，标题含“进一步规范股份减持行为”，不匹配任何上一期基准。
- **When**: 触发 `PolicyAnalyzer.analyze(policy_id)`。
- **Then**: 
  - 验证分发 `GeneralSummaryOutput` 的 Prompt；
  - 验证使用 `deepseek-v4-flash` 模型；
  - 校验合并板块函数 `merge()` 是否成功将大模型输出与 `dim_policy_keyword_sector`（如“股份减持”→“非银金融/券商”）进行排重融合。
  - 校验 `dwd_policy_analysis.cost_cny` 大于 0。

### 2.2 测试案例二：敏感领域措辞比对与 thinking 正则兜底测试
- **Given**: 输入一篇当期人行货政报告关键章节，库中存在上一期历史记录。
- **When**: 触发比对引擎，调用 `pro-thinking` 并 Mock 注入一个格式不规范但内容正确的 API 响应（外层带 Markdown 包裹的 JSON 块）。
- **Then**:
  - 验证调用 `deepseek-v4-pro` 并启用 thinking。
  - 验证正则提取引擎强力清除了 ```json 等前缀，成功解析出 JSON。
  - 校验 `intensity_change ∈ {"增强", "持平", "减弱"}` 写入物理库。

---

## 3. 可观测性与 CLS 日志设计
### 3.1 结构化 JSON 日志格式
在 `chat()` 方法中，每一次接口落地时，输出单行 JSON 日志：
```json
{
  "timestamp": "2026-05-17T18:31:00Z",
  "level": "INFO",
  "event": "llm_call_completed",
  "policy_id": 1024,
  "prompt_name": "wording_contrast",
  "prompt_version": "v2",
  "model": "deepseek-v4-pro",
  "thinking_enabled": true,
  "input_cache_hit_tokens": 12000,
  "input_cache_miss_tokens": 4000,
  "output_tokens": 800,
  "reasoning_tokens": 1500,
  "cost_cny": 0.045000,
  "duration_ms": 12450,
  "status": "success",
  "hit_rate": 0.75
}
```

### 3.2 腾讯云 CLS 日志报警阈值
在云监控 CLS 中配置告警拦截：
- **P0 级告警**：大模型调用报错状态为 `api_error`（特别是 401 密钥失效）或 `quota_exceeded`（配额爆表），立即触发邮件+微信强预警。
- **P1 级告警**：日成本追踪 `meta_llm_daily_cost.total_cost_cny` 达到 ¥4.0（日限额 80%）时触发邮件预警。

---

## 4. 第四阶段验收指标 (AC)
- **AC4.1 (近一周回填阻断)**: 运行 `backfill_policy_analysis.py` 脚本，物理数据库上仅最近一周（7天内）的 `ods_policy_info` 数据被正确捞出并执行 AI 分析，7天以前的数据绝对不被读取，杜绝超额计费。
- **AC4.2 (预算锁死)**: 设定预算上限为 ¥1.0 元进行微量灰度，验证回填到 ¥1.0 元时是否立即安全挂起。
- **AC4.3 (CLS 告警畅通)**: 故意拦截 Mock 一个 401 报错，验证 CLS 日志解析触发告警动作是否即时生效。
