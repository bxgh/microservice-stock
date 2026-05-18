# 避坑秘籍：多级路由分级调度 staged_analyzer 的避坑与物理熔断实践

> 本文档记录了在实施 `scf-collector` M1-Patch (v2 Iteration) 期间遭遇的诡异 Bug、性能瓶颈、网络/权限受阻等踩坑记录，遵循双轨制高价值技术沉淀规范。

---

## 坑位一：Windows PowerShell 终端 GBK 编码崩溃 (UnicodeEncodeError)

### 踩坑记录 (The Pitfall)
在 Windows 本地环境下运行 `verify_prompt_consistency.py` 物理对账审计时，当 Python 尝试在 Console 打印漂亮的宽字符 Emoji（如 `✅`）时，突然抛出致命的 `UnicodeEncodeError: 'gbk' codec can't encode character` 报错，导致整个审计脚本在本地终端崩溃。

### 方案对比 (Options Explored)
*   **方案 A (强制终端设置 UTF-8)**: 通过 `chcp 65001` 命令临时改变 Windows 控制台编码。
    *   *弊端*: 需要额外的系统配置或批处理脚本干预，对 AI 自动化执行或无头脚本不够友好。
*   **方案 B (Python 统一 ASCII 指示词)**: 在代码层面彻底弃用 Emoji，使用 `[OK]`、`[WARNING]`、`[HEALTH]`、`[ERROR]` 等纯 ASCII 符号进行日志格式化。
    *   *优势*: 没有任何跨平台依赖，在 Windows (GBK/UTF-8) 或 Linux 容器 (UTF-8) 下都能 100% 稳定运行。

### 择优决策 (Optimal Choice)
采用 **方案 B**。物理运维与测试脚本在终端输出时必须保持极简，避免宽字符污染以防在各种非标操作系统环境下运行中断。

---

## 坑位二：历史 Prompt 重构遗留的 API 常量割裂 (AttributeError)

### 踩坑记录 (The Pitfall)
在前人对系统 Prompt 完成了 V3 版本前缀冻结后，未能将调用端 `policy_analyzer.py` 的引用同步改写。导致线上调度器或 OMO 逆回购政策在拉起大模型分析时，尝试访问 `prompts.GENERAL_SUMMARY_SYSTEM` 会直接引发属性错误崩溃 `AttributeError: module 'shared.utils.prompts' has no attribute 'GENERAL_SUMMARY_SYSTEM'`。

### 方案对比 (Options Explored)
*   **方案 A (在 prompts.py 中保留旧常量引用)**: 保持兼容，把旧常量的变量名指向新常量。
    *   *弊端*: 会导致 prompts.py 极度臃肿，产生大面积的重复常量和技术债。
*   **方案 B (物理全局一键 Patch 并同步升级)**: 自研精准全局替换运维补丁，强行将所有的旧常量替换为最新的 `GENERAL_SUMMARY_SYSTEM_V3`，并同步将数据库中的 `prompt_name` 与 `prompt_version` 标志提级为 `"GENERAL_SUMMARY_V3"` 和 `"3.0"`。
    *   *优势*: 保持了代码库的绝对干净与强版本对齐，杜绝了老数据对新库的“隐形污染”。

### 择优决策 (Optimal Choice)
采用 **方案 B**。编写 `scratch/patch_policy_analyzer.py`，成功实现了该核心引擎的一键安全升维，彻底扫荡了该重大潜在崩溃漏洞。

---

## 坑位三：Mock 提取数据与真实提取器契约脱节 (KeyError)

### 踩坑记录 (The Pitfall)
在编写 `test_staged_analyzer.py` 熔断兜底的正常落库测试时，手动 Mock 的 OMO 字典没有对齐 `OMOExtractor.generate_summary` 所严格规定的顶级 key 契约（如缺少 `'amount_cny_100m'` 等），导致调用时在 `generate_summary` 发生 `KeyError`。

### 方案对比 (Options Explored)
*   **方案 A (将所有 extractor 宽进严出化)**: 在各个规则提取器中大量增加 `get(key, 0)` 等兼容代码。
    *   *弊端*: 会削弱金融级字段提取的严密性判定，使异常数据被错误写入主库而无法捕获。
*   **方案 B (保持强类型约束，利用 MonkeyPatch 精准测试)**:
    *   正常落库时，mock 数据结构必须对齐真实提取字典。
    *   异常熔断测试时，利用 Python 内置的 `MonkeyPatch` 特性拦截具体的 `extract` 接口，故意返回不包含核心 key 的错乱数据（如 `{"bad_key": True}`），强迫其抛出 `KeyError`，从而完美验证 `[FAILSAFE-FALLBACK]` 降级引擎。

### 择优决策 (Optimal Choice)
采用 **方案 B**。这是最顶级的软件工程测试实践，既保护了金融表前缀字段约束的强健性，又在测试中实现了对异常兜底大底座的 100% 真实物理覆盖！

---

## 复用技巧与最佳实践 (Reusable Tips)

1.  **大底座兜底防线**：设计多级路由或直切（production）模式时，在 try 块内部不仅需要拦截数据库异常，更应该在直切写入前捕捉任何可能由于正则表达式在极端环境下解析非标数据所抛出的异常（如 IndexError, KeyError）。一旦发现，立刻触发 `[FAILSAFE-FALLBACK]` 并注入 `bypass_failed=1`，强制退流大模型，确保服务绝对不停机。
2.  **大模型 Token 缓存预热技巧**：在使用 DeepSeek API 时，只要 System Prompt 及其前缀完全静态一致，官方会自动在底层做内存级 Caching（`input_cache_hit_tokens`）。日间运行或物理审计时，应确保没有诸如系统时间戳、动态 session_id 注入到 system 中，从而充分释放 90% 的降本潜力。
