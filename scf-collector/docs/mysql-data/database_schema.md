# 股东数据 数据库结构

存储位置：腾讯云 MySQL 数据库。

## 1. 股东户数表 (`stock_shareholder_count`)
记录公司随时间推移的股东人数变化。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 索引 |
| `end_date` | DATE | 截止日期 | 索引 |
| `holder_count` | INT | 股东户数 | |
| `holder_change_pct`| DECIMAL(24,6)| 户数变动比例 | 支持大比例变动 (如新股) |
| `avg_market_cap` | DECIMAL(20,2)| 户均持股市值 | 单位：元 |
| `updated_at` | TIMESTAMP | 更新时间 | 自动更新 |

- **唯一约束**: `uk_code_date (ts_code, end_date)`
- **主要查询**: 按 `ts_code` 倒序查询历史。

## 2. 前十大股东表 (`stock_top10_shareholders`)
记录各季度报告披露的前十大流通股东详情。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 索引 |
| `end_date` | DATE | 截止日期 | 索引 |
| `rank` | INT | 排名 | 1-10 |
| `holder_name` | VARCHAR(255) | 股东名称 | 前20字符索引 |
| `share_type` | VARCHAR(50) | 股份类型 | |
| `hold_count` | BIGINT(20) | 持股数量 | 单位：股 |
| `hold_pct` | DECIMAL(10,4)| 持股比例 | 单位：% |
| `change_stat` | VARCHAR(50) | 变动状态 | 增减持、新进等 |
| `updated_at` | TIMESTAMP | 更新时间 | |

- **唯一约束**: `uk_code_date_rank (ts_code, end_date, rank)`
- **主要查询**: 给定 `ts_code` 和 `end_date` 查询排名前10的名单。

---

## 3. 技术优化
- **字段扩容**: `holder_change_pct` 采用 `DECIMAL(24,6)` 是为了应对极其特殊情况下（如公司分立、回购注销、新股上市初期）可能出现的超大变动比例，防止数据库溢出报错。
- **并发控制**: 写入时使用 `ON DUPLICATE KEY UPDATE`，确保多次同步同一份数据时不会产生冗余，且能更新旧数据。

## 3. 限售股解禁表 (`stock_restricted_release`)
记录限售股解禁历史及未来计划。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 索引 |
| `release_date` | DATE | 解禁日期 | 索引 |
| `release_count` | BIGINT | 解禁数量 | 单位：股 |
| `release_market_cap` | DECIMAL(20,2)| 解禁市值 | 单位：元 |
| `ratio` | DECIMAL(10,4)| 占流通市值比 | |
| `holder_type` | VARCHAR(100) | 限售类型 | |

- **唯一约束**: `uk_code_date_type (ts_code, release_date)` (实际索引可能仅为 code+date)

## 4. 大宗交易每日明细表 (`stock_block_trade`)
记录逐笔大宗交易明细。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 索引 |
| `trade_date` | DATE | 交易日期 | 索引 |
| `price` | DECIMAL(10,2) | 成交价 | |
| `volume` | DECIMAL(20,2) | 成交量 | 单位：股 |
| `amount` | DECIMAL(20,2) | 成交额 | 单位：元 |
| `buyer` | VARCHAR(255) | 买方营业部 | |
| `seller` | VARCHAR(255) | 卖方营业部 | |

- **索引**: `idx_trade_date`, `idx_ts_code` (无唯一约束，允许单日多笔)

## 5. 龙虎榜每日明细表 (`stock_lhb_daily`)
记录龙虎榜每日汇总及机构博弈数据。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 索引 |
| `trade_date` | DATE | 交易日期 | 索引 |
| `close_price` | DECIMAL(10,4) | 收盘价 | |
| `change_pct` | DECIMAL(10,4) | 涨跌幅 | |
| `turnover_rate` | DECIMAL(10,4) | 换手率 | |
| `net_buy_amt` | DECIMAL(20,2) | 龙虎榜净买额 | |
| `reason` | TEXT | 上榜原因 | |
| `inst_net_buy_amt` | DECIMAL(20,2) | 机构净买入 | |
| `inst_buy_count` | INT | 买入机构数 | |
| `inst_sell_count` | INT | 卖出机构数 | |

- **唯一约束**: `uk_code_date (ts_code, trade_date)`

## 6. 北向资金每日持股表 (`stock_north_funds_daily`)
记录沪深股通每日个股持仓。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 索引 |
| `trade_date` | DATE | 交易日期 | 索引 |
| `hold_count` | BIGINT | 持股数量 | |
| `hold_market_cap` | DECIMAL(20,2) | 持股市值 | |
| `hold_ratio` | DECIMAL(10,4) | 持股占比 | |

- **唯一约束**: `uk_code_date (ts_code, trade_date)`

## 7. 机构评级表 (`stock_analyst_rank`)
记录分析师/机构对个股的评级变动，用于计算信息维度 $I_{analyst}$。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `stock_code` | VARCHAR(20) | 股票代码 | |
| `report_date` | DATE | 研报日期 | |
| `analyst` | VARCHAR(50) | 机构/分析师 | |
| `rating` | VARCHAR(20) | 评级 | 买入/增持等 |
| `change_direction` | VARCHAR(10) | 变动 | 维持/上调/下调 |
| `target_price` | DECIMAL(10,2) | 目标价 | |

- **唯一约束**: `uk_code_date_analyst (stock_code, report_date, analyst)`

## 8. 业绩预告表 (`stock_performance_forecast`)
记录上市公司业绩预告，用于捕捉预期差 $I_{forecast}$。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `stock_code` | VARCHAR(20) | 股票代码 | |
| `notice_date` | DATE | 公告日期 | |
| `report_period` | DATE | 报告期 | 财报截止日 |
| `type` | VARCHAR(20) | 类型 | 预增/预减/扭亏等 |
| `growth_min` | DECIMAL(10,2) | 增长下限(%) | |
| `growth_max` | DECIMAL(10,2) | 增长上限(%) | |

- **唯一约束**: `uk_code_period (stock_code, report_period)`

## 9. 市场热度统计表 (`stock_sentiment_daily`)
记录股吧等社区的每日关注度元数据，用于计算散户情绪 $I_{buzz}$。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `stock_code` | VARCHAR(20) | 股票代码 | |
| `trade_date` | DATE | 交易日期 | |
| `post_count` | INT | 发帖量 | 统计样本内 |
| `read_count` | INT | 阅读量 | 统计样本内 |
| `comment_count` | INT | 评论量 | 统计样本内 |
| `rank_score` | INT | 热度排名 | |

- **唯一约束**: `uk_code_date (stock_code, trade_date)`

## 10. 停牌数据表 (`stock_suspensions`)
记录股票每日停牌状态。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 标准后缀格式 (如 `300912.SZ`) |
| `trade_date` | DATE | 停牌日期 | |
| `is_suspended` | TINYINT | 是否停牌 | 1=是 |
| `reason` | VARCHAR(255) | 停牌原因 | |

- **唯一约束**: `uk_code_date (ts_code, trade_date)`

## 11. 早盘数据 (Pre-Market)

### 11.1 业绩预告表 (`stock_performance_forecast`)
记录上市公司发布的业绩预告、快报信息。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | |
| `ts_code` | VARCHAR(20) | 股票代码 | 标准后缀 (如 `000001.SZ`) |
| `report_period` | DATE | 报告期 | 如 `2025-12-31` |
| `notice_date` | DATE | 公告日期 | |
| `type` | VARCHAR(255) | 预告类型 | "预增", "扭亏" 等 |
| `growth_range` | VARCHAR(255) | 变动幅度 | "50% - 80%" |

- **唯一约束**: `uk_code_period (ts_code, report_period)`

### 11.2 除权除息日程表 (`stock_xr_schedules`)
记录股票的除权除息日信息。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `ts_code` | VARCHAR(20) | 股票代码 |
| `ex_date` | DATE | 除权除息日 |
| `bonus_ratio` | DECIMAL(10,4) | 送转比例 |
| `cash_div` | DECIMAL(10,4) | 派现金额 |

- **唯一约束**: `uk_code_date (ts_code, ex_date)`

---

## 12. 数据标准

### 股票代码格式 (Stock Code Format)
全系统数据库表统一遵循 **标准后缀格式**：
*   **字段名**: 通常命名为 `ts_code` 或 `stock_code`。
*   **格式**: `数字代码.后缀` (如 `603288.SH`, `301633.SZ`, `430047.BJ`)。
*   **清洗规则**: 废弃所有旧有前缀格式 (如 `sh.600000`)。存量数据已通过 `robust_migrate_codes.py` 脚本统一迁移。

## 13. 行业分类数据 (Industry Metadata)

### 13.1 申万行业 (`stock_industry_sw`)
记录申万一级、二级、三级行业分类。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | VARCHAR(20) | 股票代码 (PK) |
| `l1_code` | VARCHAR(20) | 一级行业代码 |
| `l1_name` | VARCHAR(50) | 一级行业名称 |
| `l2_code` | VARCHAR(20) | 二级行业代码 |
| `l2_name` | VARCHAR(50) | 二级行业名称 |
| `l3_code` | VARCHAR(20) | 三级行业代码 |
| `l3_name` | VARCHAR(50) | 三级行业名称 |

### 13.2 东方财富行业 (`stock_industry_em`)
作为同花顺行业的替代（因反爬），记录东方财富板块分类。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | INT | 自增主键 |
| `ts_code` | VARCHAR(20) | 股票代码 |
| `industry_code` | VARCHAR(20) | 行业代码 (如 BKxxxx) |
| `industry_name` | VARCHAR(50) | 行业名称 |

- **唯一约束**: `uk_code_ind (ts_code, industry_code)`

---

## 14. 数据质量与观测 (DQ & Observability)

### 14.1 数据质量异常项表 (`dq_findings`)
记录各类校验规则（如跨源比对、业务规则等）发现的异常。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 可为空 (全局校验) |
| `trade_date` | DATE | 交易日期 | |
| `rule_id` | VARCHAR(50) | 规则ID | 对应 `rules.yaml` 中的 ID |
| `severity` | VARCHAR(20) | 严重程度 | INFO/WARN/ERROR/CRITICAL |
| `description` | TEXT | 异常详细描述 | |
| `diff_data` | JSON | 差异数据详情 | 存储比对差异快照 |
| `status` | VARCHAR(20) | 状态 | OPEN (待处理) / RESOLVED (已解决) |
| `created_at` | TIMESTAMP | 发现时间 | |
| `updated_at` | TIMESTAMP | 最后更新时间 | |

- **索引**: `idx_trade_date`, `idx_rule_id`, `idx_status`

### 14.2 DQ 指标历史表 (`dq_metrics_history`)
记录每日数据质量核心指标的统计结果。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `trade_date` | DATE | 统计日期 | |
| `indicator_name` | VARCHAR(50) | 指标名称 | COMPLETENESS/CONSISTENCY 等 |
| `indicator_value`| DECIMAL(10,4)| 实际值 | |
| `target_value` | DECIMAL(10,4)| 目标阈值 | |
| `status` | VARCHAR(20) | 状态判定 | OK/WARNING/ERROR |
| `created_at` | TIMESTAMP | 计算时间 | |

- **唯一约束**: `uk_date_name (trade_date, indicator_name)`

---

## 15. AI 政策分析引擎 (AI Policy Tracker)

### 15.1 原始政策信息表扩展字段 (`ods_policy_info`)
对原始政策信息表进行扩展以支持分类与状态跟踪。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `policy_type` | VARCHAR(50) | 政策分类，关联 dim_policy_type | 默认 'other', 索引 |
| `analysis_status` | VARCHAR(20) | AI分析状态 | 默认 'pending_analysis', 索引 |

### 15.2 政策 AI 分析明细表 (`dwd_policy_analysis`)
记录政策的 AI 核心摘要、评级理由、受益板块、措辞对比与 MLOps 计费追踪等完整数据。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `policy_id` | INT | 关联 `ods_policy_info.id` | |
| `summary` | VARCHAR(1500) | AI 三句话摘要 (JSON 数组) | |
| `importance_level` | TINYINT | 重要性评级 1-5 | 索引 |
| `importance_reason` | VARCHAR(500) | 评级理由 | |
| `sectors_positive` | MEDIUMTEXT | 受益板块及标的 (JSON) | |
| `sectors_negative` | MEDIUMTEXT | 受损板块 (JSON) | |
| `intensity_change` | VARCHAR(20) | 强度变化：增强/持平/减弱/不适用 | 默认 'N/A', 索引 |
| `key_differences` | MEDIUMTEXT | 措辞文字差异详情 (JSON) | |
| `implication` | VARCHAR(1000) | 市场隐含影响说明 | |
| `contrast_baseline_id` | INT | 对比基准政策 id | |
| `segment_used` | MEDIUMTEXT | 实际截取用于分析的段落 | |
| `segment_extracted` | TINYINT(1) | 关键段落是否提取成功 | 默认 1 |
| `input_truncated` | TINYINT(1) | 输入是否被物理截断 | 默认 0 |
| `analysis_path` | VARCHAR(20) | 分析路径: llm/rule/rule_then_llm/cache | 默认 'llm' |
| `analysis_stage` | VARCHAR(20) | 分析阶段: triage_only/triage_and_deep/triage_and_voting | 默认 'triage_only' |
| `triage_confidence` | DECIMAL(3,2) | 初筛置信度 | 默认 1.00 |
| `triage_borderline` | TINYINT(1) | 是否因置信度不足强制升级 | 默认 0 |
| `requires_human_review` | TINYINT(1) | 是否需要人工复核 | 默认 0 |
| `voting_consistency_rate` | DECIMAL(5,4) | 投票一致率 | 默认 1.0000 |
| `core_segment_simhash` | CHAR(16) | 核心段落 simhash | |
| `prompt_name` | VARCHAR(50) | Prompt 分类 | |
| `prompt_version` | VARCHAR(10) | Prompt 版本 | |
| `model_name` | VARCHAR(50) | 使用的物理模型名 | |
| `thinking_enabled` | TINYINT(1) | 是否启用 thinking | 默认 0 |
| `reasoning_effort` | VARCHAR(10) | 思考档位 low/medium/high | |
| `input_cache_hit_tokens` | INT | 缓存命中输入 token | 默认 0 |
| `input_cache_miss_tokens` | INT | 缓存未命中输入 token | 默认 0 |
| `output_tokens` | INT | 输出 token | 默认 0 |
| `reasoning_tokens` | INT | 深度思考 token | 默认 0 |
| `cost_cny` | DECIMAL(10,6) | 单次调用实际成本 (CNY) | 默认 0.000000 |
| `is_off_peak` | TINYINT(1) | 是否为错峰时段调用 | 默认 0 |
| `raw_response` | MEDIUMTEXT | LLM 原始返回 (异常排查) | |
| `reasoning_content` | MEDIUMTEXT | 思考链中间输出 | |
| `analysis_duration_ms` | INT | 调用耗时 (ms) | 默认 0 |
| `analysis_status` | VARCHAR(20) | 处理状态 | 默认 'pending', 索引 |
| `error_message` | VARCHAR(500) | 错误报错描述 | |
| `retry_count` | TINYINT | 重试次数 | 默认 0 |
| `created_at` | TIMESTAMP | 创建时间 | 默认 CURRENT_TIMESTAMP, 索引 |
| `updated_at` | TIMESTAMP | 更新时间 | |
| `is_deleted` | TINYINT(1) | 是否逻辑删除 | 默认 0 |

- **唯一约束**: `uk_policy_prompt (policy_id, prompt_name, prompt_version)`
- **索引**: `idx_created_at_analysis_path (created_at, analysis_path)`

### 15.3 政策 AI 分析影子对照表 (`dwd_policy_analysis_shadow`)
结构与 `dwd_policy_analysis` 100% 一致。用于并行旁路验证，安全评测 Rule-Based 过滤分流机制和 LLM 模型升级对比。

### 15.4 LLM 响应缓存表 (`meta_response_cache`)
基于 prompt 属性与规范化内容的 MD5 签名缓存机制，防止因重复请求/短时间心跳导致的大量 Token 计费。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `cache_key` | CHAR(32) | MD5 唯一缓存 Key | 主键 |
| `prompt_name` | VARCHAR(50) | Prompt 模版分类名称 | |
| `prompt_version` | VARCHAR(10) | Prompt 模版版本号 | |
| `model_name` | VARCHAR(50) | 大模型名称 | |
| `response_content` | MEDIUMTEXT | 缓存的 JSON 响应体 | |
| `hit_count` | INT | 累计命中次数 | 默认 0 |
| `created_at` | TIMESTAMP | 写入时间 | 默认 CURRENT_TIMESTAMP |
| `last_hit_at` | TIMESTAMP | 上次命中/刷新时间 | 索引 |

### 15.5 LLM 日消费累计审计表 (`meta_llm_daily_cost`)
高精度的天级大模型资源计费账单表，支持区分高峰期与错峰时段复合审计。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `cost_date` | DATE | 计费日期 | 联合主键 |
| `is_off_peak` | TINYINT(1) | 是否为错峰优惠时段 (00:30-08:30) | 默认 0, 联合主键 |
| `total_cost_cny` | DECIMAL(10,6) | 当天累计支出金额 (CNY) | 默认 0.000000 |
| `total_calls` | INT | 当天累计调用次数 | 默认 0 |
| `total_input_tokens` | BIGINT | 累计输入 Token 数量 | 默认 0 |
| `total_output_tokens` | BIGINT | 累计输出 Token 数量 | 默认 0 |
| `updated_at` | TIMESTAMP | 更新时间 | |

- **唯一主键**: `PRIMARY KEY (cost_date, is_off_peak)`

---

## 16. 数据自动修复与一致性协同 (Data Repair & Consistency)

### 16.1 数据质量修复日志表 (`meta_repair_log`)
记录 Healer 自动数据修复过程，与 dq_findings 联动，支持 MySQL 到 ClickHouse 数据一致性同步确认（LSN 追踪）。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增主键 | 主键 |
| `finding_id` | INT | 关联的 `dq_findings.id` | 索引 |
| `ts_code` | VARCHAR(20) | 股票代码 | 联合索引 |
| `trade_date` | DATE | 交易日期 | 联合索引 |
| `table_name` | VARCHAR(64) | 修复的目标表名 | |
| `repair_type` | VARCHAR(32) | 修复类别 (如 CONSENSUS/MANUAL) | 默认 'CONSENSUS' |
| `source_used` | VARCHAR(32) | 修复所用数据源 (如 MOOTDX/AKSHARE/TUSHARE) | |
| `before_snapshot` | JSON | 修复前数据快照 | |
| `after_snapshot` | JSON | 修复后数据快照 | |
| `status` | VARCHAR(20) | 修复状态 (PENDING/SUCCESS/FAILED/ROLLED_BACK) | 默认 'PENDING', 索引 |
| `error_msg` | TEXT | 修复失败时的错误堆栈/信息 | |
| `sync_lsn` | BIGINT | 同步确认 LSN 位点 | 默认 0 |
| `sync_status` | VARCHAR(16) | 同步状态 (PENDING/ACKED/ORPHAN/SKIPPED) | 默认 'PENDING' |
| `created_at` | TIMESTAMP | 发现与写入时间 | |
| `updated_at` | TIMESTAMP | 更新时间 | |
| `is_deleted` | TINYINT(1) | 逻辑删除标志 | 默认 0 |

### 16.2 数据修复忽略白名单表 (`meta_repair_whitelist`)
记录人工确认无需修复、忽略校验的特例数据记录，具备过期失效机制。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 忽略的股票代码 | 联合索引 |
| `trade_date` | DATE | 忽略的交易日期 | 联合索引 |
| `rule_id` | VARCHAR(64) | 忽略的校验规则 ID | |
| `reason` | TEXT | 记录加入白名单的详细原因 | |
| `expire_at` | DATETIME | 白名单失效时间 | 联合索引 |
| `created_at` | TIMESTAMP | 创建时间 | |
| `updated_at` | TIMESTAMP | 更新时间 | |
| `is_deleted` | TINYINT(1) | 是否逻辑删除 | 默认 0, 联合索引 |

### 16.3 物理表同步位点状态表 (`meta_sync_status`)
用于多源存储（如 ClickHouse 双写/同步）的一致性 LSN 位点记录与监控。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `table_name` | VARCHAR(64) | 物理表名 | 主键 |
| `last_commit_lsn` | BIGINT | 最后一次同步成功确认的 LSN 位点 | 默认 0 |
| `last_sync_at` | DATETIME | 最后同步成功的时间戳 | |
| `status` | VARCHAR(16) | 同步链路状态 (NORMAL/DELAY/ERROR) | 默认 'NORMAL' |
| `updated_at` | TIMESTAMP | 位点刷新时间 | |

### 16.4 修复任务队列工作表 (`meta_task_queue`)
自研数据自愈队列，支撑日线缺失（Hole）、前复权因子失效、价格与成交量错配等多维自动补数。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | BIGINT UNSIGNED | 自增 ID | 主键 |
| `task_type` | VARCHAR(32) | 任务类别 (如 REPAIR_KLINE / REPAIR_FACTOR) | |
| `ts_code` | VARCHAR(16) | 股票代码 | 联合索引 |
| `trade_date` | DATE | 交易日期 | 联合索引 |
| `error_type` | ENUM | 错误大类 (HOLE / PRICE_MISMATCH / VOLUME_MISMATCH / FACTOR_STALE) | |
| `context` | JSON | 对账明细上下文 (如 `{"local": 10.1, "target": 10.0}`) | |
| `status` | ENUM | 任务执行状态 (PENDING / RUNNING / SUCCESS / FAILED) | 默认 'PENDING', 索引 |
| `retry_count` | TINYINT | 重试次数 | 默认 0 |
| `created_at` | TIMESTAMP | 创建时间 | |
| `updated_at` | TIMESTAMP | 状态更新时间 | |

### 16.5 全局系统配置表 (`meta_config`)
提供全局校验锚点、滑窗大小、系统级流控等全局环境变量的统一底座。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `config_key` | VARCHAR(100) | 配置唯一 Key | 主键 |
| `config_value` | TEXT | 配置的值 (支持存储大 JSON/XML 文本) | |
| `description` | TEXT | 配置的业务释义与目的 | |
| `updated_at` | TIMESTAMP | 最近修改时间 | |

### 16.6 数据修复历史审计表 (`meta_repair_history`)
对所有物理表底层发生的 DML 修复改动提供只读、抗篡改备份审计痕迹。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | BIGINT | 自增ID | 主键 |
| `task_id` | BIGINT UNSIGNED | 关联的修复任务 `meta_task_queue.id` | |
| `ts_code` | VARCHAR(20) | 股票代码 | 联合索引 |
| `trade_date` | DATE | 交易日期 | 联合索引 |
| `repair_type` | VARCHAR(50) | 修复操作描述 | |
| `old_value` | JSON | 被重写前的数据行快照 (用于回滚) | |
| `new_value` | JSON | 重写写入后的新数据行快照 | |
| `created_at` | TIMESTAMP | 发生历史时刻 | |

---

## 17. 行业成员与指数行情 (Industry Member & Index Kline)

### 17.1 申万行业成员拉链表 (`dim_sw_industry_member`)
记录申万成分指数对应的成分股纳入与剔除日期拉链生命周期。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `index_code` | VARCHAR(20) | 申万指数代码 | 联合唯一约束 |
| `index_name` | VARCHAR(50) | 申万指数名称 | |
| `con_code` | VARCHAR(20) | 成分股票代码 | 联合唯一约束, 索引 |
| `con_name` | VARCHAR(50) | 成分股票名称 | |
| `in_date` | DATE | 成分股纳入日期 | 联合唯一约束, 索引 |
| `out_date` | DATE | 成分股剔除日期 (NULL 为当前处于最新状态) | |
| `is_new` | VARCHAR(10) | 是否为最新成分 | |
| `created_at` | TIMESTAMP | 写入时间 | |
| `updated_at` | TIMESTAMP | 更新时间 | |
| `is_deleted` | TINYINT(1) | 逻辑删除标志 | 默认 0 |

- **唯一约束**: `uk_index_con_date (index_code, con_code, in_date)`

### 17.2 指数日线行情表 (`ods_index_daily`)
存储大盘指数、申万行业指数、概念指数的日 K 线原始层行情。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `ts_code` | VARCHAR(20) | 指数标准后缀代码 | 联合主键 |
| `trade_date` | DATE | 交易日期 | 联合主键, 索引 |
| `open` | DECIMAL(16,4) | 开盘价 | |
| `high` | DECIMAL(16,4) | 最高价 | |
| `low` | DECIMAL(16,4) | 最低价 | |
| `close` | DECIMAL(16,4) | 收盘价 | |
| `pre_close` | DECIMAL(16,4) | 昨收盘价 | |
| `change` | DECIMAL(16,4) | 涨跌额 | |
| `pct_chg` | DECIMAL(10,6) | 涨跌幅 (原始小数位) | |
| `vol` | DECIMAL(20,2) | 成交量 (手) | |
| `amount` | DECIMAL(20,2) | 成交额 (千元) | |
| `created_at` | TIMESTAMP | 写入时间 | |
| `updated_at` | TIMESTAMP | 更新时间 | |

- **复合主键**: `PRIMARY KEY (ts_code, trade_date)`

---

## 18. ODS 原始层财务数据 (Financial Data)

### 18.1 资产负债表 (`ods_fin_balancesheet`)
记录上市公司报告期末的货币资金、应收、存货、商誉、负债等总资产明细。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | BIGINT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 联合唯一, 索引 |
| `ann_date` | DATE | 公告日期 | 索引 |
| `f_ann_date` | DATE | 实际公告日期 | |
| `end_date` | DATE | 报告期 | 联合唯一, 索引 |
| `report_type` | VARCHAR(10) | 报表类型 | 联合唯一 |
| `comp_type` | VARCHAR(10) | 公司类型 | |
| `total_assets` | DECIMAL(20,4) | 资产总计 | |
| `total_liabilities` | DECIMAL(20,4) | 负债合计 | |
| `total_hldr_eqy_exc_min_int` | DECIMAL(20,4) | 股东权益合计(不含少数股东权益) | |
| `total_hldr_eqy_inc_min_int` | DECIMAL(20,4) | 股东权益合计(含少数股东权益) | |
| `monetary_funds` | DECIMAL(20,4) | 货币资金 | |
| `notes_receiv` | DECIMAL(20,4) | 应收票据 | |
| `accounts_receiv` | DECIMAL(20,4) | 应收账款 | |
| `inventory` | DECIMAL(20,4) | 存货 | |
| `goodwill` | DECIMAL(20,4) | 商誉 | |
| `short_term_borrow` | DECIMAL(20,4) | 短期借款 | |
| `long_term_borrow` | DECIMAL(20,4) | 长期借款 | |
| `created_at` | TIMESTAMP | 写入时间 | |
| `updated_at` | TIMESTAMP | 更新时间 | |
| `is_deleted` | TINYINT(1) | 是否逻辑删除 | 默认 0 |

- **唯一约束**: `uk_code_period_type (ts_code, end_date, report_type)`

### 18.2 利润表 (`ods_fin_income`)
上市公司天级营收、毛利、成本、三费以及归母净利润的原始披露。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | BIGINT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 联合唯一, 索引 |
| `ann_date` | DATE | 公告日期 | |
| `f_ann_date` | DATE | 实际公告日期 | |
| `end_date` | DATE | 报告期 | 联合唯一, 索引 |
| `report_type` | VARCHAR(10) | 报表类型 | 联合唯一 |
| `comp_type` | VARCHAR(10) | 公司类型 | |
| `basic_eps` | DECIMAL(10,4) | 基本每股收益 | |
| `diluted_eps` | DECIMAL(10,4) | 稀释每股收益 | |
| `total_revenue` | DECIMAL(20,4) | 营业总收入 | |
| `revenue` | DECIMAL(20,4) | 营业收入 | |
| `total_cogs` | DECIMAL(20,4) | 营业总成本 | |
| `oper_cost` | DECIMAL(20,4) | 营业成本 | |
| `sell_exp` | DECIMAL(20,4) | 销售费用 | |
| `admin_exp` | DECIMAL(20,4) | 管理费用 | |
| `fin_exp` | DECIMAL(20,4) | 财务费用 | |
| `operate_profit` | DECIMAL(20,4) | 营业利润 | |
| `total_profit` | DECIMAL(20,4) | 利润总额 | |
| `net_profit` | DECIMAL(20,4) | 净利润 | |
| `n_income_attr_p` | DECIMAL(20,4) | 归属于母公司所有者的净利润 | |
| `created_at` | TIMESTAMP | 写入时间 | |
| `updated_at` | TIMESTAMP | 更新时间 | |
| `is_deleted` | TINYINT(1) | 是否逻辑删除 | 默认 0 |

- **唯一约束**: `uk_code_period_type (ts_code, end_date, report_type)`

### 18.3 现金流量表 (`ods_fin_cashflow`)
上市公司核心经营活动产生的现金流量净额、企业自由现金流量明细。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | BIGINT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 联合唯一, 索引 |
| `ann_date` | DATE | 公告日期 | |
| `f_ann_date` | DATE | 实际公告日期 | |
| `end_date` | DATE | 报告期 | 联合唯一, 索引 |
| `report_type` | VARCHAR(10) | 报表类型 | 联合唯一 |
| `comp_type` | VARCHAR(10) | 公司类型 | |
| `net_cash_flows_oper_act` | DECIMAL(20,4) | 经营活动产生的现金流量净额 | |
| `net_cash_flows_inv_act` | DECIMAL(20,4) | 投资活动产生的现金流量净额 | |
| `net_cash_flows_fnc_act` | DECIMAL(20,4) | 筹资活动产生的现金流量净额 | |
| `free_cashflow` | DECIMAL(20,4) | 企业自由现金流量 | |
| `created_at` | TIMESTAMP | 写入时间 | |
| `updated_at` | TIMESTAMP | 更新时间 | |
| `is_deleted` | TINYINT(1) | 是否逻辑删除 | 默认 0 |

- **唯一约束**: `uk_code_period_type (ts_code, end_date, report_type)`

### 18.4 财务指标表 (`ods_fin_indicators`)
衍生出的每股净资产、每股未分配利润、ROE、资产负债率、销售净利率等分析指标。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | BIGINT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 联合唯一, 索引 |
| `ann_date` | DATE | 公告日期 | |
| `end_date` | DATE | 报告期 | 联合唯一, 索引 |
| `eps` | DECIMAL(10,4) | 每股收益 | |
| `dt_eps` | DECIMAL(10,4) | 稀释每股收益 | |
| `total_revenue_ps` | DECIMAL(20,4) | 每股营业总收入 | |
| `revenue_ps` | DECIMAL(20,4) | 每股营业收入 | |
| `capital_rese_ps` | DECIMAL(20,4) | 每股资本公积 | |
| `undist_profit_ps` | DECIMAL(20,4) | 每股未分配利润 | |
| `roe` | DECIMAL(10,4) | 净资产收益率 | |
| `roe_dt` | DECIMAL(10,4) | 净资产收益率(摊薄) | |
| `roa` | DECIMAL(10,4) | 总资产报酬率 | |
| `netprofit_margin` | DECIMAL(10,4) | 销售净利率 | |
| `grossprofit_margin` | DECIMAL(10,4) | 销售毛利率 | |
| `debt_to_assets` | DECIMAL(10,4) | 资产负债率 | |
| `current_ratio` | DECIMAL(10,4) | 流动比率 | |
| `quick_ratio` | DECIMAL(10,4) | 速动比率 | |
| `created_at` | TIMESTAMP | 写入时间 | |
| `updated_at` | TIMESTAMP | 更新时间 | |
| `is_deleted` | TINYINT(1) | 是否逻辑删除 | 默认 0 |

- **唯一约束**: `uk_code_period (ts_code, end_date)`
