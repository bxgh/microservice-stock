# Implementation Plan - E14-S2: AI 分析层与措辞对比 (AI Intelligence)

实现基于 AI 的政策监控分析与敏感领域（特别是央行货币政策）的措辞强度对比。通过结构化的 AI 智能分析，提炼政策精髓，辅助最终投资决策。

## 1. Readiness Check (AGENTS.md)

- [x] **需求解析**:
  1. **异步 LLM 客户端 (`LLMClient`)**: 采用原生 `httpx.AsyncClient` 封装 OpenAI 兼容的 HTTP API，避免打包笨重的三方库（如 `openai` SDK），保障腾讯云 SCF 环境下的轻量性（内存 ≤ 128MB）与二进制审计安全（零 `.pyd` 红线）。
  2. **Prompt 模板库**: 建设专用的 Policy Prompts 库，包含“通用摘要及评级（1-5星）”与“货币政策措辞细粒度对比”两套核心 Prompt。
  3. **措辞对比引擎 (`PolicyAnalyzer`)**: 实现政策 AI 分析落库。对于央行（`ts_code = 'PBC'`）的货币政策发布，能自动在数据库中追溯“上一期”发布文本，并与当期文本一并传入 LLM 进行强度变化（增强/持平/减弱）与细粒度增删字的对比分析。
  4. **表结构物理存储 (`dwd_policy_analysis`)**: 在 MySQL 5.7 中建立标准 DWD（明细）层表结构，保存 AI 分析结果，包含尾部三件套。
- [x] **依赖认证**:
  - 已经拥有就绪的 `ods_policy_info` 表及 1000+ 条历史数据。
  - 本地测试阶段通过 Mock LLM API 确保不消耗实际 Token，且有集成测试能验证真实接口连通性。
- [x] **角色激活**:
  - `[Requirement Architect]`: 负责 Given-When-Then 的 AC 设计和事件编排。
  - `[Backend Engineer]`: 负责轻量级异步 `LLMClient` 及措辞分析引擎开发。
  - `[DB Auditor]`: 负责 `dwd_policy_analysis` 的 DDL 设计，保证字段 and 索引的 MySQL 5.7 兼容性。
  - `[Workflow Guard]`: 负责物理真源证据的收集和验收闭环。

---

## 2. 详细技术方案

### 2.1 数据库结构升级（DDL 审计）
根据 `AGENTS.md` 的 DDL 审计要求，在 `migrations/` 目录下新增 `V1.6_E14_S2_Policy_Analysis_Tables.sql`。
表名定义为 `dwd_policy_analysis` (政策分析明细表)：
- `id` INT AUTO_INCREMENT PRIMARY KEY
- `policy_id` INT NOT NULL COMMENT '关联 ods_policy_info.id'
- `summary` TEXT NOT NULL COMMENT 'AI 三句话摘要'
- `sectors_impact` TEXT COMMENT '影响板块与代表标的 (JSON 格式)'
- `importance_level` INT COMMENT '重要性评级 (1-5 星)'
- `importance_reason` VARCHAR(255) COMMENT '评级理由'
- `wording_contrast` TEXT COMMENT '措辞变化细节对比 (仅 PBC 包含)'
- `intensity_change` VARCHAR(20) DEFAULT 'N/A' COMMENT '强度变化：增强/持平/减弱/不适用'
- `key_differences` TEXT COMMENT '文字增删等关键差异细节 (JSON 格式)'
- `implication` TEXT COMMENT '市场隐含影响'
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
- `is_deleted` TINYINT(1) DEFAULT 0
- 唯一索引 `uk_policy_id` (`policy_id`) 保证单条政策仅生成一份有效的 AI 分析结果。
- 索引 `idx_intensity_change` (`intensity_change`)，`idx_importance_level` (`importance_level`)。

### 2.2 轻量级异步 `LLMClient`
在 [llm_client.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/llm_client.py) 中：
1. 使用 `httpx.AsyncClient` 编写异步网络请求，控制标准超时为 30s。
2. 支持从环境变量 `.env` 中加载以下配置（提供 `.env.example` 占位）：
   - `LLM_API_KEY` (API 密钥)
   - `LLM_BASE_URL` (默认: `https://api.deepseek.com/v1`)
   - `LLM_MODEL` (默认: `deepseek-chat`)
3. **熔断与指数退避重试 (Resilience)**:
   - 遭遇速率限制 (429) 或网络抖动时，实施最大 3 次退避重试（初始延迟 1s，按 2^n 指数递增），确保高可用。

### 2.3 场景化 Prompt 库
在 [prompts.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/prompts.py) 中定义系统提示词：
1. **通用摘要 Prompt (`GENERAL_SUMMARY_PROMPT`)**:
   - 约束 LLM 必须以 JSON 格式输出 `summary` (三句话摘要), `importance_level` (1-5星), `importance_reason` (理由), `sectors_positive` (受益板块及标的), `sectors_negative` (受损板块)。
2. **措辞对比 Prompt (`WORDING_CONTRAST_PROMPT`)**:
   - 当遇到央行（`ts_code = 'PBC'`）政策发布时，对比上一期和当期的发布表述。
   - 约束 LLM 必须以 JSON 格式输出 `summary` (三句话摘要), `importance_level`, `intensity_change` (增强/持平/减弱), `key_differences` (文字删加、换字等差异数组), `implication` (市场隐含影响)。

### 2.4 AI 分析核心引擎 (`PolicyAnalyzer`)
在 [policy_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/analyzers/policy_analyzer.py) 中：
1. **查找上一期政策**:
   - 如果当前政策是 `PBC`，通过 SQL 查找最新一条发布日期小于当前政策日期的 `ods_policy_info` 记录。
2. **Prompt 调度与执行**:
   - 若存在上一期记录，使用 `WORDING_CONTRAST_PROMPT` 进行深度双向措辞对比分析。
   - 否则（或对于其他机构如 `CSRC`），使用 `GENERAL_SUMMARY_PROMPT` 进行通用摘要分析。
3. **结构化 JSON 解析与容错**:
   - 严格采用 `json.loads` 解析 LLM 返回值，防止其在 JSON 外包裹 Markdown 标记（利用正则或字符串截取清理 ```json 前缀）。
   - 解析异常时提供保底默认解析字段，写入 WARN 日志，严禁静默失败。
4. **落库落子**:
   - 封装 Pydantic 校验模型，保证落库字段对齐并利用 `ON DUPLICATE KEY UPDATE` 保证幂等执行。

---

## 3. 拟修改与新增文件清单

#### [NEW] [V1.6_E14_S2_Policy_Analysis_Tables.sql](file:///e:/gitee/microservice-stock/scf-collector/migrations/V1.6_E14_S2_Policy_Analysis_Tables.sql)
- 编写 MySQL 5.7 规范的 `dwd_policy_analysis` DDL 升级脚本，包含 DDL 三件套。

#### [NEW] [llm_client.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/llm_client.py)
- 实现极简异步 `LLMClient`，实现超时控制与 3 次指数退避重试。

#### [NEW] [prompts.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/prompts.py)
- 定义场景化的系统与用户 Prompt 模板，硬性约定输出 JSON 结构。

#### [NEW] [policy_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/shared/analyzers/policy_analyzer.py)
- 实现政策 AI 分析调度引擎，支持查找人行历史政策做措辞比对。

#### [MODIFY] [index.py](file:///e:/gitee/microservice-stock/scf-collector/functions/policy_monitor/index.py)
- 在采集执行完成后，自动串联执行 AI 分析。
- 升级微信通知与邮件 HTML 报告的 AI 提炼排版。

#### [MODIFY] [.env.example](file:///e:/gitee/microservice-stock/.env.example)
- 增加 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 的占位文档，符合全局通用禁令。

#### [NEW] [test_policy_analyzer.py](file:///e:/gitee/microservice-stock/scf-collector/tests/test_policy_analyzer.py)
- 编写 AI 场景分析的单元与集成测试，覆盖 Mock LLM 响应下的正确 Prompt 调用与解析。

---

## 4. 验证计划

### Automated Tests
- 运行 Pytest 进行 Mock LLM 与 Analyzer 测试：
  ```bash
  pytest tests/test_policy_analyzer.py -v
  ```
- **Given**: 输入一篇 `CSRC` 政策
- **When**: 触发 `PolicyAnalyzer` 引擎
- **Then**: 验证其分配了通用摘要 Prompt，并能成功解析出 JSON 各项字段并落库

- **Given**: 输入当期 `PBC` 政策，且库中存在上期 `PBC` 政策
- **When**: 触发措辞对比引擎
- **Then**: 验证其正确抓取了上期政策文本，分配了措辞对比 Prompt，解析出强度变化（如 `增强`）后入库

### Manual Verification
- 在 Docker 本地测试环境配置真实 LLM API Key，拉取最新一条人行或证监会公告进行端到端全管道真实调用。
- 物理检查 MySQL `dwd_policy_analysis` 表，确保字段内容、字符集完美，并且已正确关联 `policy_id`。
- 人工查收微信和邮件，确认格式完美呈现政策核心评级与措辞增删细节。
