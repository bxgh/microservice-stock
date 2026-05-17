# E14-S2 AI 政策分析引擎与措辞对比 Master 规划方案书 (v2.0)

本方案作为 E14-S2 的全局主控规划书，梳理 AI 政策分析与措辞强度比对的 Roadmap。详细的物理设计与 DDL/代码级约束已细分为 4 个子文档群。

---

## 1. 细分设计子文档群指引

> [!IMPORTANT]
> 为保障极高水平的工程可读性与阶段性评审，技术实施方案已细化为以下 4 个独立物理文档：

| 实施阶段 | 核心技术范畴 | 详细设计书物理路径 (可直接点击) |
|---|---|---|
| **Phase 1** | 物理 DDL 审计、OpenAI SDK 引入、异步 `LLMClient` 接口与计费熔断 | [phase_1_infra.md](file:///e:/gitee/microservice-stock/scf-collector/docs/features/policy-tracker/implementation_logs/E14/S2/iterations/v2/phase_1_infra.md) |
| **Phase 2** | 政策类型分类器、长文段落切片、Prompt 缓存命中对齐与 JSON 防崩正则解析 | [phase_2_analyzer.md](file:///e:/gitee/microservice-stock/scf-collector/docs/features/policy-tracker/implementation_logs/E14/S2/iterations/v2/phase_2_analyzer.md) |
| **Phase 3** | 三云函数物理拆分、并发行级锁、异步状态机队列与 HTML 高阶渲染通知 | [phase_3_scf.md](file:///e:/gitee/microservice-stock/scf-collector/docs/features/policy-tracker/implementation_logs/E14/S2/iterations/v2/phase_3_scf.md) |
| **Phase 4** | Given-When-Then 用例、断点续传回填脚本、¥50 预算控制与 CLS 告警监控 | [phase_4_backfill.md](file:///e:/gitee/microservice-stock/scf-collector/docs/features/policy-tracker/implementation_logs/E14/S2/iterations/v2/phase_4_backfill.md) |

---

## 2. User Review Required (设计准则与重要提示)

- **API 限制与红线规避**:
  DeepSeek V4 在启用 `thinking` 模式下，API 协议**无法支持** `json_object` 强制限制。
  *方案*：Flash/非思考Pro模式开启 `json_object` 强校验；`pro-thinking` 模式不传该参数，但由 Prompt 约束并在代码层使用正则稳健解析 `{.*}`，防止 API 崩溃。
- **SCF 超时防御与解耦**:
  密集政策发布日同步串联执行大模型必超 900 秒执行限制。
  *方案*：将单体云函数物理拆分为 `policy_collector`（探测落库）、`policy_analyzer`（批处理 AI 写入，含并发事务锁）及 `policy_notifier`（高星预警分发）。

---

## 3. Open Questions (设计确认)

- **Q1: 申万行业分类对齐**: 板块影响的关联表 `dwd_policy_sector_impact` 字段 `sector_code_sw` 将锁定采用 6 位标准的申万二级代码（例如 `801120` 代表半导体），代表标的限制为 Tushare 口径（例如 `600519.SH`）。此数据口径是否对齐已有的投研体系？
- **Q2: 自动回填预算上限**: 历史 1000+ 条数据回填预计消耗 token 成本约合 ¥11.6 元（DeepSeek V4 官方折后价）。回填脚本中我们将设置 ¥50 元的硬熔断防护。该预算限额是否可行？

---

## 4. 总体度量指标

### 4.1 业务与成本指标
- 重要政策 (`importance_level >= 4`) 的 AI 分析覆盖率 = 100%
- 大模型日消费超出 ¥5.0 元限额时，熔断警报畅通。
- 大模型月度分析与运营成本核算偏差 ≤ 30%。

### 4.2 技术指标
- JSON 解析成功率 ≥ 99% (利用 `json_object` 与正则兜底双重加固)。
- 系统 Prompt 缓存命中率 (Prompt Caching hit rate) ≥ 60%。
- 单个 AI 分析云函数每次运行耗时 ≤ 15 秒（由于 5 条/批批处理限制与长文切片算法支持）。
