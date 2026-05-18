# Implementation Plan - E15-E4: Prefix-Freeze 缓存改造

本方案针对 AI 政策分析引擎中的 E4 阶段（Prefix-Freeze 缓存改造）开展详细的设计与实施规划。本阶段的核心目标是将大模型 Prompt 缓存命中率从基线的 10.3% 大幅提升至 80%（目标 90%）以上，通过 System/User Message 结构锁死、心跳预热保活、错峰智能调度以及修复 LLM 客户端关键 Bug，全面达成月度大模型开销降本 87% 的终极财务与效率目标。

---

## 需求解析与核心逻辑 (3句话)

1. **Bug 修复与消息结构锁死**：修复 `llm_client.py` 中 `deepseek-chat` 调用时 `messages` 变量未定义的严重运行时 NameError 缺陷，确保非 reasoner 调用以“完全静态的 System Prompt (长度 $\ge 1000$ tokens) + 仅包含动态政策的 User Message”结构发起，实现字节级前缀锁死。
2. **主动心跳与保活预热 (keepalive)**：实现 `scratch/keep_alive.py` 轻量级主动预热与保活工具，在业务闲时（排除 00:30-08:30 错峰时段）每 30 分钟发起一次静默保活心跳，防止 DeepSeek 官方侧的静态前缀缓存被 cold-start 驱逐。
3. **可观测性监控与错峰核算**：利用已有的 `monitor_cache_hit_rate.py` 实施 P1/P2 级缓存命中率（低于 60%/30%）自动预警，并配合 `OffPeakScheduler` 在回填与测试任务中深度释放错峰 50% 的成本收益。

---

## 激活角色说明

*   `[Macro Policy Architect] (宏观政策架构师)`：负责审查静态 System Prompt 与 Few-shot 的锁死方案，评估长 System 垫厚对于金融分类与摘要质量的稳定度。
*   `[Data Integrity Steward] (数据质量掌门人)`：负责缓存命中率、日累计成本统计的准确性，以及心跳保活脚本对于物理分析明细账目的“非业务污染”判定。
*   `[Senior Python Backend Engineer] (资深异步后端工程师)`：负责修复 `llm_client.py` 结构缺陷，编写保活心跳与 TTL 探测机制，并完成测试环境下的双跑比对和 HTML 自动化编译部署。

---

## User Review Required

> [!IMPORTANT]
> **1. llm_client.py 隐藏缺陷修复**
> *   **Bug 诊断**：当前 `llm_client.py` 中由于 `if "deepseek-reasoner" in model:` 分支定义了 `messages` 变量，而 `else:` 分支（针对 `deepseek-chat`）仅定义了 `kwargs`，漏掉了对 `messages` 的组装，直接导致在调用 `deepseek-chat` 时会发生 `NameError` 崩溃。本方案在 `else` 分支中补齐标准的 System + User 双消息契约，为 `TRIAGE_CLASSIFIER_V1`（Flash初筛）提供绝对稳定的运行保障。
> 
> **2. 缓存保活心跳（Heartbeat）低成本保活**
> *   **频率与策略**：每 30 分钟使用极简 Prompt 作为 User Message，搭配静态 `GENERAL_SUMMARY_SYSTEM_V3` 系统提示词发起一次调用。每次仅消耗极微量 Token，单次计费 $< \text{¥}0.0001$，每月保活开销 $< \text{¥}0.05$。
> *   **错峰屏蔽**：由于北京时间 `00:30 - 08:30` 为官方错峰时段（天然低价且批处理高频运行本身会自然预热），心跳脚本在此时间窗内**自动暂停**以规避无意义的物理调度。
> *   **业务数据去污**：保活调用的统计数据将特殊写入 `meta_llm_daily_cost`，但不会写入面向终端消费的 `dwd_policy_analysis` 物理业务表中，保持业务账目的纯净。
> 
> **3. 缓存 TTL 探测逻辑**
> *   为探测 DeepSeek 缓存的最佳生存期（TTL），我们将编写 `scratch/detect_cache_ttl.py` 独立测试工具，间隔 1h, 2h, 4h, 8h 发起探测调用，验证缓存命中率的变化曲线，从而通过数据支撑决定心跳的最优间隔。

---

## Open Questions

> [!NOTE]
> **Q1: 心跳保活调用的 `call_type` 如何与常规业务调用区分以防成本混淆？**
> *   **决策**：在更新 `meta_llm_daily_cost` 表的 `_update_daily_cost` 方法中，我们会支持 `is_heartbeat` 可选参数，在心跳调用时仅增加 Token 与折算成本，但不将其记录于 `dwd_policy_analysis` 业务事实表中，确保 MLOps 审计时心跳成本可剥离、可回溯。

---

## Proposed Changes

### Component: LLM Async Client Hardening

---

#### [MODIFY] [llm_client.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/llm_client.py)
*   **修改内容**：
    1. 修复 `NameError: name 'messages' is not defined` 缺陷：在 `else` 分支（针对 `deepseek-chat` 模型）中正确组装 `messages` 列表（包含 system 与 user 两个元素）。
    2. 引入 `is_heartbeat` 机制：在 `chat()` 中支持参数透传，确保心跳调用仅更新 `meta_llm_daily_cost` 仪表盘，跳过业务表 `dwd_policy_analysis` 写入，且自动更新日累计配额审计。
    3. 规范化并对齐 message 前缀：
       ```python
       else:
           kwargs = {"temperature": temperature}
           messages = [
               {"role": "system", "content": system_prompt},
               {"role": "user", "content": user_prompt}
           ]
       ```

---

### Component: Cache Warmup & TTL Detection Utilities

---

#### [NEW] [keep_alive.py](file:///e:/gitee/microservice-stock/scf-collector/scratch/keep_alive.py)
*   **修改内容**：实现定时缓存心跳保活脚本。
*   **核心逻辑**：
    1. 调用 `OffPeakScheduler.is_off_peak()` 判断当前是否属于错峰低价时段。若为 True，直接跳过保活，保持静默。
    2. 使用 `GENERAL_SUMMARY_SYSTEM_V3`（大长 System Prompt）和极简 user 提问 `"请确认缓存热度"` 发起 `LLMClient.chat(..., mode="deep", prompt_name="HEARTBEAT_KEEP_ALIVE")`。
    3. 打印本次心跳调用的 `input_cache_hit_tokens` and `cost_cny` 统计，确保其成功命中（以极低成本保活）。
    4. 本脚本将在 SCF 环境中绑定 30 分钟定时器或在主机中配置为 cron 任务。

---

#### [NEW] [detect_cache_ttl.py](file:///e:/gitee/microservice-stock/scf-collector/scratch/detect_cache_ttl.py)
*   **修改内容**：探查 DeepSeek Prompt Cache TTL 驱逐时效的独立自动化测试脚本。
*   **核心逻辑**：
    1. 构造一个独特的长静态 system 文本。
    2. 立即发起一次调用进行 preheat（预热），记录本次为 miss。
    3. 随后按照预设的梯度时差（如 10 分钟、30 分钟、60 分钟、120 分钟），执行异步休眠并再次调用。
    4. 统计在何种等待时段后，第二阶段调用退化为 cache miss，输出最优 of TTL 探查报告。

---

## AI 实施蓝图与提示词 (Plan-as-Prompt)

> [!IMPORTANT]
> **Subagent 执行指南 (必读)**
> 1. **Bug 彻底修复**：重写 `llm_client.py` 时的 `messages` 装配必须在 mock 与真实物理环境下完全对齐，确保 `chat()` 流程百分之百跑通。
> 2. **心跳去污控制**：心跳调用严禁触碰 `dwd_policy_analysis` 业务表的写入，以防分析事实表灌入大量 `"HEARTBEAT"` 脏记录破坏下游数据分析。
> 3. **HTML 自动化编译**：所有修改 & 新增的文档（如 `implementation_plan.md`, `walkthrough.md`）开发完毕后，必须运行 `python scripts/md_to_html_premium.py <path_to_md>` 全自动构建同名 HTML 版并刷新 Portal 门户。

---

## Verification Plan

### Automated Tests
*   **缓存 Bug 与首跑命中集成测试**：
    *   在 `tests/test_prefix_freeze.py` 中编写集成用例。
    *   **测试 1：Bug 修复校验**：使用 Mock 或真实客户端，调用 `llm_client.chat` (mode="flash")，验证 `deepseek-chat` 能够正常执行且不再抛出 `NameError`。
    *   **测试 2：缓存心跳保活**：调用 `keep_alive.py` 中的核心逻辑，验证在非错峰时段发出的心跳被正确记录为 heartbeat 且在错峰时段自动跳过。
*   **运行指令**：
    ```bash
    $env:PYTHONPATH="."; pytest tests/test_prefix_freeze.py -s -v
    ```

### Manual Verification
*   在 sandbox 开发环境运行 `python scratch/keep_alive.py`，观察其对于缓存命中和 cost 的打印日志。
*   直连 MySQL 数据库，查询 `SELECT * FROM meta_llm_daily_cost ORDER BY cost_date DESC LIMIT 5`，确认心跳次数 and 累计成本已被平滑记账且未在 `dwd_policy_analysis` 中产生脏数据。
