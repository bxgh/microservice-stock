# Task List - E14-S2: AI 政策分析引擎与措辞对比 4 阶段实施清单 (v2.0)

## ── Phase 1: 数据库迁移与大模型客户端基建 ──

- [x] `[E14-S2-P1-T1]` 编写并执行迁移脚本 `V1.6_E14_S2_Policy_Analysis_Tables.sql`
    - [x] `ALTER TABLE ods_policy_info`：新增 `policy_type` 与 `analysis_status` 并创建二级索引，检查 MySQL 5.7 兼容性。
    - [x] `CREATE TABLE dwd_policy_analysis`：AI 分析明细表 DDL，设立联合主键 `uk_policy_prompt (policy_id, prompt_name, prompt_version)`。
    - [x] `CREATE TABLE meta_llm_daily_cost`：日累计成本审计表 DDL。
- [x] `[E14-S2-P1-T2]` 编写并执行迁移脚本 `V1.7_E14_S2_Sector_Impact.sql`
    - [x] `CREATE TABLE dwd_policy_sector_impact` : 板块影响扁平明细表 DDL。
    - [x] `CREATE TABLE dim_policy_keyword_sector` : 板块关键词规则种子配置表 DDL。
    - [x] 使用 `INSERT INTO` 初始化 50+ 个申万行业核心关键词→申万二级板块的对照记录。
- [x] `[E14-S2-P1-T3]` 引入 `openai>=1.30.0` 依赖并配置环境变量
    - [x] 在 `requirements.txt` 中添加依赖，并验证打包对 SCF 的包体影响。
    - [x] 修改 `.env.example` 并同步本地 `.env`，填入 `DEEPSEEK_API_KEY`、`LLM_BASE_URL`。
- [x] `[E14-S2-P1-T4]` 实现轻量级异步大模型客户端 `llm_client.py`
    - [x] 基于 `openai` AsyncOpenAI 初始化，配置超时 30s 与指数退避重试机制。
    - [x] 编写精确计费逻辑（支持 cache_hit/cache_miss 与 reasoning token 单独核算）。
    - [x] 实现 `LLM_DAILY_COST_LIMIT_CNY` 配额防刷熔断及 token 上限主动拦截。
- [x] `[E14-S2-P1-T5]` 升级自研 JSON 状态机流水接口 `log_pipeline_run_v2`
    - [x] 在 `scf-collector/shared/db/dao.py` 中重构扩展 `log_pipeline_run_v2`，完整接入并解析 `output_summary JSON` 字段。
    - [x] 编写测试脚本验证 `JSON_EXTRACT` 正确性。

---

## ── Phase 2: Prompt 模板工程与 AI 政策分析引擎 ──

- [x] `[E14-S2-P2-T1]` 建立场景化 Prompt 注册中心 `prompts.py`
    - [x] 注册 `GENERAL_SUMMARY_V2` 与 `WORDING_CONTRAST_V2` (带 few-shot 案例)。
    - [x] 隔离 system 与 user 消息，通过对齐字节提升 DeepSeek Prompt 缓存命中率。
- [x] `[E14-S2-P2-T2]` 实现政策分类器 `policy_classifier.py`
    - [x] 编写基于政策标题的正则分类算法（首发），识别 LPR、MLF、货币政策报告等。
    - [x] 编写 `deepseek-v4-flash` 兜底分类调用（备发），确保 `policy_type` 绝对被捕获。
- [x] `[E14-S2-P2-T3]` 实现长文切片提取器 `segment_extractor.py`
    - [x] 实现针对货政执行报告等特大文本的章节提取正则，单独拎出“下一阶段主要政策思路”。
    - [x] 编写 fallback 截取算法（前4000字+后2000字）防提取失败。
- [x] `[E14-S2-P2-T4]` 编写 AI 分析核心引擎 `PolicyAnalyzer`
    - [x] 实现 `find_previous_policy`，通过 `policy_type` 检索上一期基准，退化时走通用分析。
    - [x] 实现 JSON 容错解析引擎，专门针对 thinking 模式下被剔除 `json_object` 强制限制后的 Regex 兜底。
    - [x] 编写行业匹配融合类 `SectorMapper`，将 LLM 产出板块与 `dim_policy_keyword_sector` 命中结果进行去重并扁平化落库至 `dwd_policy_sector_impact`。
    - [x] 封装 Pydantic 并实现 `dwd_policy_analysis` 的幂等落库（基于 `uk_policy_prompt` 的 DUPLICATE UPDATE 机制）。

---

## ── Phase 3: SCF 函数异步化拆分与分发预警 ──

- [x] `[E14-S2-P3-T1]` SCF 云函数物理拆分与目录重整
    - [x] 移除原有同步单体函数，划分为 `policy_collector`、`policy_analyzer`、`policy_notifier` 目录。
    - [x] 编写并验证各云函数的独立定时触发机制。
- [x] `[E14-S2-P3-T2]` 实现并发唯一锁与批处理队列
    - [x] 在 `policy_analyzer` 启动时建立基于唯一索引/锁机制 of 防重入守护。
    - [x] 实现 `policy_analyzer` 每次最多拉取 5 条 `pending_analysis` 政策进行串行解析。
- [x] `[E14-S2-P3-T3]` 实现重要政策微信与 HTML 邮件通知
    - [x] 编写简洁易读的微信文本简报。
    - [x] 编写基于响应式设计的 HTML 邮件模板，高亮显示三句话摘要、强度变化（红/蓝/慢颜色展示）与板块标的。
    - [x] 对已发送政策在数据库标记为 `notified` 防重复推送。
- [x] `[E14-S2-P3-T4]` 接入 JSON 流水契约写入
    - [x] 对拆分后的 Collector, Analyzer, Notifier 独立云函数出口，编写 `log_pipeline_run_v2` 调用，落地结构化 JSON 流水成果数据。

---

## ── Phase 4: 全量历史回填与 CLS 可观测性 ──

- [x] `[E14-S2-P4-T1]` 编写并执行自动化单元测试
    - [x] 在 `tests/test_policy_analyzer.py` 中编写Given-When-Then测试。
    - [x] 验证 `GENERAL_SUMMARY_V2` 与 `WORDING_CONTRAST_V2` 的 Mock/真实运行输出。
- [x] `[E14-S2-P4-T2]` 编写近一周灰度回填脚本 `backfill_policy_analysis.py`
    - [x] 实现过滤条件，仅捞取近一周（7天内）的 `ods_policy_info` 数据进行 AI 回填，杜绝历史冗余处理。
    - [x] 实现断点续传（通过 pending 状态判断），避免重复分析与计费。
    - [x] 设定 ¥1 元的硬熔断防护，按 publish_date 倒序运行。
- [x] `[E14-S2-P4-T3]` 部署可观测性与局部门户同步
    - [x] 部署结构化 JSON 日志记录。
    - [x] 编写交付技术完工报告 `REPORT.html` 与避坑 KB。
    - [x] 运行全局 Portal 自动整合脚本。
