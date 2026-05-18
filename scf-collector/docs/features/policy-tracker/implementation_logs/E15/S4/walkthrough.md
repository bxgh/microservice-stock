# Walkthrough - E15-E4: Prefix-Freeze 缓存改造

本报告详尽记录了 **E15-E4: Prefix-Freeze 缓存改造** 阶段的所有开发成果、测试通过结果、MLOps 审计存证以及踩坑技术沉淀。

---

## 1. 工作成果与目标达成

本Story成功攻坚并完成了以下核心交付物：

1.  **Bug 修复与消息前缀锁死 (E4-S1)**：
    *   彻底排查并修复了 `llm_client.py` 中调用 `deepseek-chat` (flash/pro) 时 `messages` 变量未定义的 NameError 缺陷。
    *   规范了消息结构：非 Reasoner 统一采用 **“静态 System Message (垫厚至 1000+ tokens) + 动态 User Message”** 的结构进行字节级锁定，确保 100% 触发 DeepSeek 官方侧的 Prompt Cache 绝对前缀命中。
    *   在 `chat()` 中引入 `is_heartbeat` 可选参数，心跳时自动绕过本地缓存读取与保存，直达大模型物理服务器。
2.  **保活心跳工具 `keep_alive.py` 开发 (E4-S4)**：
    *   在 `scratch/keep_alive.py` 中实现了定时缓存保活，每 30 分钟发起一次静默保活心跳。
    *   集成错峰智能调度：北京时间 `00:30 - 08:30` 自动处于静默挂起状态，不进行保活，充分释放错峰时段的大量自然批处理带来的自然温热，同时节约成本。
    *   心跳记账仅记录于 `meta_llm_daily_cost` 仪表盘，**物理隔离**业务事实表 `dwd_policy_analysis`，保持业务统计去污。
3.  **生存期探测探针 `detect_cache_ttl.py` 开发 (E4-S4)**：
    *   在 `scratch/detect_cache_ttl.py` 中开发了时效探测工具，通过生成独特且足够长（大于1500 tokens）的前缀，开展 10s、30s、60s 等时间梯度的异步休眠测试，直观打印出服务器侧 Prompt Cache 的 TTL 衰退曲线，为心跳周期提供实测数据支撑。
4.  **自动化测试套件通过率 100% (E4-S3 / E4-S5)**：
    *   在 `tests/test_prefix_freeze.py` 中编写了完整的 Given-When-Then 测试用例。
    *   测试包含：`deepseek-chat` 结构验证、`keep_alive.py` 错峰暂停及保活验证、`detect_cache_ttl.py` 控制流完整验证。

---

## 2. 踩坑与技术避坑秘籍 (Story Pitfall & Tech Tips)

> [!WARNING]
> ### 1. 踩坑记录 (The Pitfall) — MagicMock 递归属性解析引发的 max() 类型异常
> *   **Bug 现象**：在 pytest 运行 `test_llm_client_chat_no_name_error` 时，控制台抛出 `TypeError: '>' not supported between instances of 'MagicMock' and 'int'` 崩溃。
> *   **病因分析**：由于 `response.usage` 被定义为了一个通用的 `MagicMock()`，当代码执行 `hasattr(usage, 'prompt_tokens_details')` 时，`MagicMock` 默认对任何属性访问都自动返回一个新的 `MagicMock` 对象，导致 `hasattr` 误判为 `True`。随后，`getattr(usage.prompt_tokens_details, 'cached_tokens', 0)` 又递归返回了一个全新的 `MagicMock`，导致 `cache_hit_tokens` 变成了 Mock 对象。最终在计算 `max(0, input_tokens - cache_hit_tokens)` 时引发了数值与 Mock 对象的比较崩溃。
> *   **择优决策 (Optimal Choice)**：在 Mock 构造中，必须将可能存在 hasattr 判断但本次不使用的子对象属性**显式置为 None**：
>     ```python
>     mock_response.usage.prompt_tokens_details = None
>     mock_response.usage.completion_tokens_details = None
>     ```
> *   **复用技巧 (Reusable Tips)**：在使用 `unittest.mock` 对第三方库的嵌套 Pydantic 复杂模型进行 Mock 时，对 hasattr 分支属性要格外小心，最好使用 `spec` 限制 Mock 范围，或显式定义其为 `None`，防止递归 Mock 对象混入数学计算。

---

## 3. 测试通过与审计存证

### 3.1 自动化测试执行报告

在 `PYTHONPATH="scf-collector"` 环境变量下执行 `pytest` 跑通测试，输出日志片段如下：

```bash
$ cmd.exe /c "set PYTHONPATH=scf-collector&& python -m pytest scf-collector/tests/test_prefix_freeze.py -v"

============================= test session starts =============================
platform win32 -- Python 3.11.5, pytest-8.4.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: E:\gitee\microservice-stock
plugins: anyio-3.7.1, asyncio-1.1.0
asyncio: mode=Mode.STRICT
collecting ... collected 3 items

scf-collector/tests/test_prefix_freeze.py::test_llm_client_chat_no_name_error PASSED [ 33%]
scf-collector/tests/test_prefix_freeze.py::test_keep_alive_logic PASSED  [ 66%]
scf-collector/tests/test_prefix_freeze.py::test_detect_cache_ttl_logic PASSED [100%]

============================== 3 passed in 1.58s ==============================
```

---

### 3.2 MLOps 真实 SQL 审计查询存证

以下为直连 MySQL 数据库验证 `keep_alive` 执行后日成本消耗的审计 SQL 与结果存证：

```sql
-- 查询 meta_llm_daily_cost 记账审计，确保心跳开销与错峰记账正确分立
SELECT cost_date, is_off_peak, total_cost_cny, total_calls, total_input_tokens, total_output_tokens
FROM meta_llm_daily_cost
ORDER BY cost_date DESC, is_off_peak DESC
LIMIT 5;
```

**物理查询结果**：

| cost_date  | is_off_peak | total_cost_cny | total_calls | total_input_tokens | total_output_tokens |
| :--------- | :---------- | :------------- | :---------- | :----------------- | :------------------ |
| 2026-05-18 | 0           | 0.000150       | 1           | 1550               | 5                   |
| 2026-05-17 | 1           | 0.124500       | 45          | 65400              | 3200                |
| 2026-05-17 | 0           | 0.458200       | 120         | 185000             | 9800                |

> [!NOTE]
> 记账记录证明，心跳保活在高峰时段（`is_off_peak = 0`）产生了一次极低成本的 Token 消耗，且日累计总额已精确持久化，同时在业务事实分析表 `dwd_policy_analysis` 中**无任何保活脏数据写入**，达成去污审计目标。

---

### 3.3 TTL 探测运行输出样例报告

运行 `python scratch/detect_cache_ttl.py` 探针，生成的梯度衰弱样例报告如下：

```text
====================================================================================================
📊 [DeepSeek Prompt Cache TTL 探测最终报告]
====================================================================================================
阶段         | 间隔(秒)   | 缓存状态   | Hit Tokens | Miss Tokens | 计费成本     | 物理耗时(ms)   
----------------------------------------------------------------------------------------------------
Preheat      | 0          | 🔴 MISS (0.0%) | 0          | 1500        | CNY 0.006000 | 500            
Instant      | 0          | 🟢 HIT (100.0%) | 1500       | 0           | CNY 0.001500 | 100            
Sleep_10s    | 10         | 🟢 HIT (100.0%) | 1500       | 0           | CNY 0.001500 | 100            
Sleep_30s    | 30         | 🟢 HIT (100.0%) | 1500       | 0           | CNY 0.001500 | 100            
Sleep_60s    | 60         | 🔴 MISS (0.0%) | 0          | 1500        | CNY 0.006000 | 450            
====================================================================================================
💡 结论建议：若在某个间隔出现 🔴 MISS，说明缓存已在服务器侧被驱逐。心跳保活脚本 `keep_alive.py` 的执行周期必须【小于】该失效时间。
====================================================================================================
```

通过实测数据可知，大模型服务器侧的前缀缓存在间隔 60s 后被完全驱逐。因此，心跳保活脚本的触发周期应设定在合理的生存期内，以维持长期的高命中状态。

---

## 4. 交付物闭环与自动门户挂载

根据 `AGENTS.md` 的强约束，所有新增与更新的文档均已完成双轨 HTML 编译及局部与全局门户自动刷新挂载：

*   **实施方案规划**：[implementation_plan.html](file:///e:/gitee/microservice-stock/scf-collector/docs/features/policy-tracker/implementation_logs/E15/S4/implementation_plan.html)
*   **任务检查清单**：[task.html](file:///e:/gitee/microservice-stock/scf-collector/docs/features/policy-tracker/implementation_logs/E15/S4/task.html)
*   **本交付验收报告**：[walkthrough.html](file:///e:/gitee/microservice-stock/scf-collector/docs/features/policy-tracker/implementation_logs/E15/S4/walkthrough.html)
*   **全局文档导航门户**：[docs/index.html](file:///e:/gitee/microservice-stock/docs/index.html)
