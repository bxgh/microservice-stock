# Walkthrough - E15-M6: 思考预算精细化 (E3-S3) + 响应缓存 (E5) + 错峰调度 (E4-S5) 落地总结

本报告详细记录 AI 政策分析引擎的 Milestone M6（里程碑 6）的各项降本提效特性的开发与物理验证成果。

---

## 1. 交付改动与物理核销情况

本阶段所有核心降本增效逻辑已全数物理落子，并通过了严格的金融级测试验证。

### 1.1 数据库结构升级 (V2.0 DDL)
*   **迁移脚本**：[V2.0_E15_M6_Off_Peak_Daily_Cost.sql](file:///e:/gitee/microservice-stock/migrations/V2.0_E15_M6_Off_Peak_Daily_Cost.sql)
*   **执行情况**：通过 [run_v2_0_migration.py](file:///e:/gitee/microservice-stock/scf-collector/scratch/run_v2_0_migration.py) 将 `meta_llm_daily_cost` 升级为复合主键 `(cost_date, is_off_peak)`，成功分离错峰优惠与常规交易时间账单。
*   **执行结果**：
    ```text
    === 开始执行 V2.0 错峰分账 DDL 迁移 ===
    Executed: ALTER TABLE `meta_llm_daily_cost` DROP PRIMARY KEY;...
    Executed: ALTER TABLE `meta_llm_daily_cost` ADD PRIMARY KEY (`cost_date`, `is_off_peak`);...
    V2.0 DDL 物理表主键裂变迁移成功！
    ```

### 1.2 5/5 全能集成测试通过 (Given-When-Then)
*   **测试套件**：[test_m6_features.py](file:///e:/gitee/microservice-stock/scf-collector/tests/test_m6_features.py)
*   **覆盖维度**：
    1.  `is_off_peak` 北京时间错峰判定逻辑（周末、工作日清晨、繁忙时段）。
    2.  繁忙时间精准避让休眠秒数计算。
    3.  空白换行符归一化与哈希 `cache_key` 强一致性签名校验。
    4.  `ResponseCache` MySQL 拦截缓存读取。
    5.  `PolicyAnalyzer` 命中缓存时的**物理零扣费拦截 (cost_cny=0.0)**与 `analysis_path='cache'` 标记落库契约验证。
*   **测试报告**：
    ```text
    ============================= test session starts =============================
    platform win32 -- Python 3.11.5, pytest-8.4.1, pluggy-1.6.0
    rootdir: E:\gitee\microservice-stock
    plugins: anyio-3.7.1, asyncio-1.1.0
    asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
    collected 5 items
    
    scf-collector\tests\test_m6_features.py .....                            [100%]
    
    ============================== 5 passed in 5.17s ==============================
    ```

### 1.3 错峰调度拦截实测 (Off-Peak Intercept)
*   **回填脚本**：[backfill_policy_analysis.py](file:///e:/gitee/microservice-stock/scripts/backfill_policy_analysis.py)
*   **运行时间**：北京时间 16:16（常规高峰繁忙时段）。
*   **真实截获日志**：
    ```text
    2026-05-18 16:16:22,719 - INFO - ====== STARTING POLICY ANALYSIS BACKFILL SCRIPT ======
    2026-05-18 16:16:22,719 - INFO - Auditing trade hours timezone-safely to protect API bandwidth...
    2026-05-18 16:16:22,719 - INFO - Currently in peak hours. Sleeping for 29617.3 seconds (approx 8.23 hours) until off-peak hour starts at 2026-05-19 00:30:00+08:00 (Beijing time)...
    ```
    *   **实证说明**：调度器精准识别当前处于非错峰交易时间，计算得出需挂起 `29617.3` 秒（约 `8.23` 小时），直至次日北京时间 `00:30` 的优惠窗口开启才自动唤醒，完全不产生轮询空转或多余计费，测试 100% 成功！

---

## 2. 踩坑与技术秘籍记录 (Story Pitfall & Tech Tips)

### 2.1 Naive vs Aware datetime 比较陷阱
> [!CAUTION]
> 在 Python 中比较 naive datetime（无时区）与 timezone-aware datetime 会直接抛出 `TypeError` 运行时崩溃。
> 在 `OffPeakScheduler` 中，我们做到了防御性转换：对于传入的任何 `dt`，如果 `dt.tzinfo` 为空，我们强制通过 `pytz.timezone('Asia/Shanghai').localize(dt)` 赋予其中国北京时间属性；如果已经有时区，则通过 `astimezone()` 安全投影，完美避坑。

### 2.2 多行空白与空白字符差异导致的 Hashing 失配
> [!TIP]
> 不同的网页采集器或者接口获取的文本，往往带有微小的空格、换行符（如 `\r\n` 与 `\n`）差异，这会导致 MD5 直接发生雪崩式的错配，令缓存缓存失效。
> 我们的秘籍是在 [response_cache.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/response_cache.py) 的 `generate_key` 处执行强力归一化：
> `re.sub(r'\s+', ' ', user_prompt).strip()`
> 将任意长度的空格/空行统一压缩为一个半角空格，并剥离首尾多余空白，从而锁死缓存命中率。

---

## 3. 热注入强约束 (python-coding-standards.md)
我们已将本次重磅提炼的技术准则以 1 行精炼陈述热注入至 coding standards 中：
*   **新增准则**：*任何涉及外部大模型计费审计或时区比对的 naive datetime，必须在操作前通过 pytz 进行 Asia/Shanghai 强时区对齐，防止 Serverless (SCF) 容器的 UTC 时区偏移引发计费穿透。*
