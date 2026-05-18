# Implementation Plan - E15-M6: 思考预算精细化 (E3-S3) + 响应缓存 (E5) + 错峰调度 (E4-S5) 落地

本方案针对 AI 政策分析引擎的 Milestone M6（里程碑 6）进行详细设计与实施规划。该里程碑包含三个可并行的提效降本 Story：
1. **E3-S3 思考预算精细化**：根据政策类型与重要性分级动态调度大模型思考档位（`reasoning_effort`），避免无节制空转。
2. **E5 应用层响应缓存 (E5-S1)**：对相同 Prompt 签名和政策内容的请求通过 MySQL 执行秒级直接命中缓存，阻断重复计费。
3. **E4-S5 错峰时段调度**：为历史回填等非实时批处理任务增加 localized 北京时间错峰识别，自动在 00:30 - 08:30 时段自动调度并结算 50% 折扣。

---

## 需求解析与核心逻辑 (3句话)

1. **精细化思考调度**：将默认一刀切的 reasoning 档位重构为基于 `(policy_type, importance_level)` 二维矩阵 of 动态查找配置，为常规公告自动匹配 `high`（低消耗）而仅为超重磅宏观政策解锁 `max`（高火力）。
2. **高精度缓存拦截**：实现基于 MD5 签名的 MySQL 应用层缓存器，拦截相同的 LLM 提问并返回完整缓存响应（包括思考链），同时将 `analysis_path` 设为 `cache` 且成本归零。
3. **北京时间错峰执行**：利用 `pytz` 严格锁定 `Asia/Shanghai` 时区校验，在 00:30-08:30 时段内自动更新 `meta_llm_daily_cost` 记录的 `is_off_peak`，并令批处理任务在此优惠窗口内无缝休眠与触发。

---

## 激活角色说明

*   `[Macro Policy Architect] (宏观政策架构师)`：负责定义场景与思考力匹配 of 金融合理性，防范预算降级影响分析质量。
*   `[Data Integrity Steward] (数据质量掌门人)`：负责缓存的强一致性签名哈希算法设计、淘汰治理、以及天级错峰明细库设计。
*   `[Senior Python Backend Engineer] (资深异步后端工程师)`：负责 `pytz` 时差安全调度逻辑、`asyncio.sleep` 精准计算、YAML 加载及应用层缓存接入。

---

## User Review Required

> [!IMPORTANT]
> **1. DeepSeek V4 reasoning_effort 档位映射**
> *   DeepSeek V4 当前官方仅支持 `high` 和 `max` 档位（原 `low`/`medium` 会被官方自动映射到 `high`）。本方案中，YAML 配置文件将这几档合并映射。普通 4 星深度分析默认映射为 `high`，仅 5 星超重磅政策且涉及重要决策时，映射为 `max` 以激发最强逻辑推理。
> 
> **2. meta_llm_daily_cost 主键裂变 (PrimaryKey Alter)**
> *   由于每天可以同时产生“正常时段调用”与“错峰折半调用”，为了高精度审计，我们将 `meta_llm_daily_cost` 表的主键从原有的 `cost_date DATE` 改写为复合主键 `PRIMARY KEY (cost_date, is_off_peak)`。这样 `ON DUPLICATE KEY UPDATE` 就能全自动分流、并统计出每天这两档的累计费用，设计精妙。
> 
> **3. 缓存淘汰策略 (Eviction Policy)**
> *   我们设计了轻量级的“30天未使用”主动清理机制，通过查询 `last_hit_at < NOW() - INTERVAL 30 DAY` 清除冷数据，每月由定时任务 or 触发器跑一次，保障云数据库存储极其轻量。

---

## Open Questions

> [!NOTE]
> **Q1: 缓存中是否需要保留大模型的推理思考链 (reasoning_content)？**
> *   **决策**：必须保留。如果下游通知或者调试看板需要渲染“思考过程”，缓存数据必须完整复现。因此我们将 `ResponseCache` 中存储的内容定义为**整个 LLM 返回字典的 JSON 序列化字符串**，Retrieved 时再无缝解开。这样既能 100% 恢复 content、reasoning_content 等所有物理契约字段，还能保留原始模型名，体验极其真实。

---

## Proposed Changes

### Component: Database Migrations & Configurations

---

#### [NEW] [V2.0_E15_M6_Off_Peak_Daily_Cost.sql](file:///e:/gitee/microservice-stock/migrations/V2.0_E15_M6_Off_Peak_Daily_Cost.sql)
*   **修改内容**：执行 `meta_llm_daily_cost` 表的主键升级与错峰字段注入。
*   **代码结构**：
    ```sql
    -- 1. 修改 meta_llm_daily_cost 主键，增加 is_off_peak 区分错峰账单
    ALTER TABLE `meta_llm_daily_cost` DROP PRIMARY KEY;
    ALTER TABLE `meta_llm_daily_cost` ADD COLUMN `is_off_peak` TINYINT(1) DEFAULT 0 COMMENT '是否为错峰时段' AFTER `cost_date`;
    ALTER TABLE `meta_llm_daily_cost` ADD PRIMARY KEY (`cost_date`, `is_off_peak`);
    ```

---

#### [NEW] [reasoning_effort_matrix.yaml](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/reasoning_effort_matrix.yaml)
*   **修改内容**：建立政策类型和重要性级别对齐 `reasoning_effort` 思考档位的矩阵映射。
*   **配置内容**：
    ```yaml
    # 场景化大模型思考档位矩阵映射表
    # DeepSeek V4 映射规范: 5星重磅 -> max; 4星普通/措辞对比 -> high; 默认 -> high
    monetary_policy_report:
      4: "high"
      5: "max"
    government_work_report:
      4: "high"
      5: "max"
    regulation_release:
      4: "high"
      5: "high"
    default:
      4: "high"
      5: "high"
    ```

---

### Component: Cache Layer & Scheduling Utilities

---

#### [NEW] [response_cache.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/response_cache.py)
*   **修改内容**：全新应用层大模型响应缓存管理器。
*   **核心逻辑**：
    1.  `generate_key(prompt_name, prompt_version, model_name, user_prompt)`: 清理空白与换行进行一致性规范化，随后执行 MD5 生成 32 位 cache_key。
    2.  `async def get(cache_key)`: 查询 `meta_response_cache`。若命中，更新 `hit_count = hit_count + 1` 与 `last_hit_at`，返回反序列化后的字典响应，同时注入 `is_cache_hit = True`。
    3.  `async def set(cache_key, prompt_name, prompt_version, model_name, response_dict)`: 将完整的 chat 返回字典序列化并灌入物理库。
    4.  `async def evict_cold_data(days=30)`: 物理清空超过 30 天未被命中的冷数据。

---

#### [NEW] [off_peak_scheduler.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/off_peak_scheduler.py)
*   **修改内容**：北京时区安全的错峰分析调度器。
*   **核心逻辑**：
    1.  `is_off_peak(dt: datetime = None)`: 使用 `pytz` 强制将本地/云端时间转化为 `Asia/Shanghai`，比对当前是否处于 `00:30` - `08:30` 的北京优惠时段。
    2.  `async def wait_for_off_peak()`: 针对批处理场景，如果当前处于高峰期，精准计算秒级时差（例如下午 14:00 离线触发，系统会自动睡眠并静默等待 `(24:00 - 14:00) + 30 分钟`），到次日 00:30 自动唤醒，不造成任何 CPU 轮询空转。

---

### Component: Core Analysis Engine Upgrade

---

#### [MODIFY] [llm_client.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/llm_client.py)
*   **修改内容**：
    1.  引入时区调度器 `OffPeakScheduler` 替代原有的 `datetime.datetime.now().time()` 判定，解决云端 SCF 环境中 UTC 时间偏移导致的错峰结算误判。
    2.  在 `chat()` 接口入口注入 `ResponseCache` 查询拦截：
        *   哈希定位 cache_key。如果命中了应用层响应，直接将 `cost_cny` 覆盖为 `0.000000`，各项 tokens 设为 0，标记 `is_cache_hit=True` 后光速退出，完全跳过 API 物理请求。
        *   若未命中，在完成常规 LLM 请求后，静默将结果持久化至 `meta_response_cache`。
    3.  `chat()` 接口支持 `reasoning_effort: Optional[str] = None` 自定义入参。若传入且调用 `deepseek-reasoner` 时，自动装入 `kwargs["reasoning_effort"]` 中随 completions 请求一起发送给 DeepSeek。
    4.  更新 `_update_daily_cost` 物理插入账单逻辑，新增并持久化 `is_off_peak` 参数，适配复合主键，实现精确的分级每日审计。

---

#### [MODIFY] [policy_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/policy_analyzer.py)
*   **修改内容**：
    1.  `analyze_policy` 新增入参 `reasoning_effort: Optional[str] = None` 并透传至 `llm_client.chat`。
    2.  在进行最终 `dwd_policy_analysis` 物理写入时，如果 `llm_result.get("is_cache_hit")` 为真：
        *   强制将 `analysis_path` 写入为 `'cache'`。
        *   将落库的 Token 消耗、推理 Token 消耗以及 `cost_cny` 统统强制覆盖为 `0`，体现应用层拦截收益。

---

#### [MODIFY] [staged_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/staged_analyzer.py)
*   **修改内容**：
    1.  类初始化时加载并缓存 `reasoning_effort_matrix.yaml` 配置字典。
    2.  设计内部函数 `_resolve_reasoning_effort(policy_type: str, importance: int) -> str`，根据当前的政策属性与初筛星级匹配出对应的 `reasoning_effort`。
    3.  在二阶段路由树（`triage_and_deep` 与 `triage_and_voting`）中，自动解析出当前的最优思考档位，并随 `analyze_policy(row, reasoning_effort=...)` 透传，实现精细化思考预算控制。

---

### Component: Bulk Ingestion Batch Scripts

---

#### [MODIFY] [backfill_policy_analysis.py](file:///e:/gitee/microservice-stock/scripts/backfill_policy_analysis.py)
*   **修改内容**：
    1.  在离线历史数据回填主函数 `main()` 入口的最上方增加对 `wait_for_off_peak()` 的前置拦截。
    2.  支持通过 `OFF_PEAK_SCHEDULING_ENABLED` 环境变量（默认 `true`）控制是否在启动时强制等候至北京错峰优惠时间才发起跑片。

---

## AI 实施蓝图与提示词 (Plan-as-Prompt)

> [!IMPORTANT]
> **Subagent 执行指南 (必读)**
> 1.  **高精密 cache_key 哈希**：在 `response_cache.py` 中，计算 cache_key 前，必须先对 user_prompt 的空白换行等用 `strip()` 和 `re.sub(r'\s+', ' ', ...)` 归一化，防止因为空格或者空行格式微小偏差导致缓存失效。
> 2.  **复合主键升级优先**：必须首先在 MySQL 数据库中执行 `V2.0_E15_M6_Off_Peak_Daily_Cost.sql` 升级主键，确保 `_update_daily_cost` 写入带 `is_off_peak` 参数时不会报 Primary Key 冲突。
> 3.  **时区一致性**：在 `off_peak_scheduler.py` 中，严禁使用任何 `datetime.now()` 裸类。必须显式通过 `pytz.timezone('Asia/Shanghai')` 强转为中国北京标准时间，从而完美对抗腾讯云 SCF 默认的 UTC 0 时区容器环境。
> 4.  **HTML 全自动构建**：所有修改 or 新增的 markdown 文档均须执行 `python scripts/md_to_html_premium.py <file>` 编译 HTML 副本并自动刷新 Portal 门户。

---

## Verification Plan

### Automated Tests
*   **Milestone M6 特性全覆盖集成测试**：
    *   我们将在 `tests/test_m6_features.py` 中编写标准 Given-When-Then 集成用例。
    *   **缓存命中测试**：连续两次灌入同一 mock 政策：第一次触发物理 LLM 请求并完成入库，第二次拦截 LLM 返回 `is_cache_hit=True`，并确认 `analysis_path='cache'` 且单次 Token 与计费成本为 0.0。
    *   **思考档位测试**：验证输入 monetary_policy_report + 5星，能成功 resolve 出 `max` 档位；输入 regulation_release + 4星，resolve 出 `high` 档位。
    *   **错峰计算与等待测试**：Mock 不同时段的时间戳：下午 14:00 校验 `is_off_peak=False`，且等待器计算出精确睡眠时差；清晨 03:00 校验 `is_off_peak=True`，且等待器光速通过无需睡眠。
    *   **运行命令**：
        ```bash
        $env:PYTHONPATH="."; pytest tests/test_m6_features.py -s -v
        ```

### Manual Verification
*   在 sandbox 运行环境设置 `OFF_PEAK_SCHEDULING_ENABLED=true` 运行 `python scripts/backfill_policy_analysis.py`。
*   人工检查日志，核实其在白天运行时是否成功被 `OffPeakScheduler` 拦截并显示“*Currently in peak hours. Sleeping... until off-peak...*”。
*   使用 DBeaver/Datagrip 直连开发数据库：
    *   查询 `meta_response_cache` 确认生成的 `cache_key` 格式正确且 `response_content` 包含完整的 json 结构。
    *   查询 `meta_llm_daily_cost` 验证当天产生了 `is_off_peak=0` 与 `is_off_peak=1` 条分立账单流水。
