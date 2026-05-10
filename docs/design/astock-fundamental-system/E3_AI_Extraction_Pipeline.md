# E3 AI 抽取流水线

对研究池(~200 只)做深度信息抽取,从年报、调研纪要、业绩说明会中提取结构化基本面信息。**这是 AI 真正的主战场**。预计耗时 3 周。

## 存储策略

抽取结果采用**双层存储 + 按报告期归档 + Schema 版本管理**:

**双层存储**:
- **原始层 `ads_extracted_facts`**(JSON 字段):AI 抽取的完整结构化结果,带 `source_quote` 溯源,Schema 灵活可演进。**事实源**。
- **消费层 `ads_company_metrics`**(扁平宽表):从 JSON 解析出高频查询字段(研发占比、毛利率、客户集中度等),供 L4/L5/L6/L7 高效查询。**查询优化层**,从原始层定时同步,可重建。

设计取舍:纯 JSON 查询性能差(MySQL 5.7 的 JSON path 索引能力有限),纯宽表 Schema 演进困难。双层结构兼顾抽取灵活性和查询性能。

**按报告期归档**(关键):
- 每只公司每个 `report_period`(如 `2024A`、`2024Q3`)对应一条记录,**不覆盖历史**
- 原因:基本面分析的核心是看变化轨迹(研发占比演化、客户集中度趋势),不是看最新值

**Schema 版本管理**:
- `ads_extracted_facts` 表用 `(ts_code, report_period, schema_version)` 三元组作为唯一约束
- Schema 升级(如新增"产能利用率"字段)时,版本号 +1,**老数据不重抽**,新抽取用新 Schema
- 消费层宽表添加新字段时,允许老数据为 NULL,业务层做 NULL safe 处理
- 跨版本对比时,只对比共有字段

---

## E3-S1 文档预处理与分段

**作为** AI 抽取层的上游,**我希望** 长文档被合理分段以适配模型上下文窗口,**以便** AI 调用既准确又经济。

### 任务

- E3-S1-T1 实现年报章节切分器(识别"管理层讨论与分析"、"主要会计数据和财务指标"、"董事报告"、"风险因素"等章节)
- E3-S1-T2 调研纪要保持完整不切分(通常较短)
- E3-S1-T3 业绩说明会按 Q&A 切分
- E3-S1-T4 切分结果存储为 JSON,字段包括 `section_id`, `section_name`, `text`, `position_anchor`(原文位置标记,用于溯源)

### 验收标准

- **AC1**: 年报章节识别
  - **Given** 一份完整年报 Markdown 文件
  - **When** 执行 `preprocess_annual_report.py`
  - **Then** 输出 JSON 包含至少 5 个核心章节(主营业务、财务分析、研发投入、风险因素、公司治理),每个章节文本完整且 `position_anchor` 可定位回原文段落

---

## E3-S2 抽取 Prompt 与 Schema 设计

**作为** AI 抽取的设计者,**我希望** 抽取 Prompt 输出结构化 JSON 且必须带原文溯源,**以便** 下游可以信任和验证抽取结果。

### 任务

- E3-S2-T1 定义抽取 Schema(主营业务结构、客户集中度、研发投入、产能规划、政策依赖、风险因素)
- E3-S2-T2 设计抽取 Prompt(强制 JSON 输出 + 强制原文引用 + 不确定标 `null`)
- E3-S2-T3 实现 Schema 校验器(`pydantic` 或 `jsonschema`)
- E3-S2-T4 设计抽取失败处理策略(JSON 解析失败 → 重试 1 次 → 标记 failed)
- E3-S2-T5 设计 Prompt 模板(避免幻觉的关键约束)

### 设计:抽取 Schema(部分核心字段)

```yaml
business_breakdown:        # 主营业务拆分
  - product_name: str       # 产品/服务名称
    revenue_yoy: float      # 营收同比(%)
    revenue_share: float    # 营收占比(%)
    gross_margin: float     # 毛利率(%)
    source_quote: str       # 原文引用(必填)
    source_section: str     # 原文章节
customer_concentration:    # 客户集中度
  top5_share: float         # 前五大客户占比(%)
  top1_share: float         # 第一大客户占比(%)
  is_related_party: bool    # 是否关联方
  source_quote: str
rd_investment:             # 研发投入
  rd_amount: float          # 研发金额(万元)
  rd_to_revenue: float      # 研发占营收比(%)
  rd_capitalization_ratio: float  # 研发资本化率(%)
  rd_personnel: int         # 研发人员数量
  source_quote: str
policy_dependency:         # 政策依赖度
  subsidy_amount: float     # 政府补助金额(万元)
  subsidy_to_profit: float  # 补助/净利润(%)
  tax_preference: bool      # 是否享受税收优惠
  source_quote: str
key_risks:                 # 风险因素(自由文本列表)
  - risk_description: str
    source_quote: str
```

### Prompt 设计原则(关键约束)

```
1. "如果原文没有明确数据,字段必须填 null,严禁推测或编造"
2. "每个字段必须配 source_quote,引用原文不超过 30 字"
3. "如果发现数据矛盾,在 conflicts 字段中说明"
4. "输出 JSON 必须能被 Python json.loads 直接解析"
```

### 验收标准

- **AC1**: Schema 一致性
  - **Given** 一份年报已切分
  - **When** 调用 AI 抽取
  - **Then** 输出 JSON 通过 `pydantic` Schema 校验,所有非 null 字段必须有 `source_quote`,空值字段标记为 `null` 而非空字符串

- **AC2**: 幻觉控制
  - **Given** 一份不包含明确客户集中度数据的年报
  - **When** AI 抽取 `customer_concentration`
  - **Then** `top5_share` 和 `top1_share` 必须为 `null`,而不是编造数字

- **AC3**: 原文溯源
  - **Given** AI 输出 `business_breakdown[0].revenue_yoy=35.2`
  - **When** 在原文中搜索 `source_quote`
  - **Then** 该 quote 必须在原文中存在(允许标点空格差异),否则抽取结果作废

---

## E3-S3 批量抽取调度与缓存

**作为** 系统使用者,**我希望** AI 抽取有缓存机制,**以便** 不重复消耗 API 配额。

### 任务

- E3-S3-T1 设计抽取任务表 `meta_extract_tasks`(ts_code, report_period, status, retry_count, cost_tokens)
- E3-S3-T2 实现批量抽取调度器(并发 5 个 worker,避免触发 API 限频)
- E3-S3-T3 抽取结果缓存:同一 `(ts_code, report_period, schema_version)` 已抽取过则跳过
- E3-S3-T4 模型分层调用:Sonnet 4.6 主力,Opus 4.7 仅用于"产业链推断"等复杂任务
- E3-S3-T5 成本统计:每次抽取记录 token 消耗,生成月度成本报表

### 验收标准

- **AC1**: 增量抽取
  - **Given** 研究池中某公司新发布 2024 年报
  - **When** E1-S3 抓取完成后触发
  - **Then** 该公司 2024 年报被加入抽取队列,完成抽取后写入 `ads_extracted_facts` 表,且 `meta_extract_tasks` 状态变为 `completed`

- **AC2**: 缓存命中
  - **Given** 某公司 2023 年报已抽取过
  - **When** 重新执行抽取流程
  - **Then** 系统识别到 `(ts_code, report_period, schema_version)` 已存在,跳过抽取,节省 token

- **AC3**: 成本可控
  - **Given** 每月抽取 ~200 只公司全部财报和纪要
  - **When** 月底生成成本报表
  - **Then** 月度 AI 调用成本 ≤ ¥1000(TBD,如超出需触发优化:更小模型、更短 prompt、更激进缓存)

---

## E3-S4 抽取结果校验

**作为** 数据消费者,**我希望** 抽取结果在使用前自动校验,**以便** 错误数据不会污染下游。

### 任务

- E3-S4-T1 实现 source_quote 原文存在性校验
- E3-S4-T2 数值合理性校验(毛利率不能 > 100%,占比之和 ≤ 100%+5% 容差)
- E3-S4-T3 财务数值与 Tushare 财报数据交叉对比(如果 AI 抽出的研发金额与 Tushare 财务数据偏差 > 10%,标记为 `needs_review`)
- E3-S4-T4 校验失败的记录进入人工复核队列

### 验收标准

- **AC1**: 溯源校验
  - **Given** AI 抽取结果中包含 `source_quote`
  - **When** 执行 `validate_extraction.py`
  - **Then** 在原文中搜索 `source_quote`(允许 token 级模糊匹配),未找到的字段被标记 `valid=false`,不进入下游

- **AC2**: 数值合理性
  - **Given** 抽取结果中 `gross_margin=120.5`
  - **When** 数值校验
  - **Then** 该字段被标记异常,告警通知人工复核

---

## E3-S5 抽取结果的扁平宽表同步

**作为** 下游分析层(L4/L5/L6/L7),**我希望** 抽取结果有一份扁平宽表副本,**以便** 我能用直观的 SQL 高效查询,而不必每次都解析 JSON。

### 任务

- E3-S5-T1 设计 `ads_company_metrics` 宽表 Schema(高频查询字段为主,详见附录 A)
- E3-S5-T2 实现 JSON → 宽表的同步脚本 `sync_facts_to_metrics.py`
  - 全量重建:从 `ads_extracted_facts` 重新生成全部宽表数据(用于 Schema 升级或异常修复)
  - 增量同步:基于 `ads_extracted_facts.created_at` 时间戳增量
- E3-S5-T3 字段映射配置文件 `config/metrics_mapping.yaml`,声明每个宽表字段对应 JSON 中的 path
- E3-S5-T4 同步任务接入 E6 触发器(原始层有更新 → 触发宽表同步)
- E3-S5-T5 关键字段建索引(`ts_code`, `report_period`, 行业相关字段),物化视图加速跨公司聚合查询

### 字段映射示例

```yaml
# config/metrics_mapping.yaml
metrics_mapping:
  - target_field: rd_to_revenue
    json_path: $.rd_investment.rd_to_revenue
    type: decimal(8,4)
  - target_field: rd_capitalization_ratio
    json_path: $.rd_investment.rd_capitalization_ratio
    type: decimal(8,4)
  - target_field: top5_customer_share
    json_path: $.customer_concentration.top5_share
    type: decimal(8,4)
  - target_field: top1_customer_share
    json_path: $.customer_concentration.top1_share
    type: decimal(8,4)
  - target_field: subsidy_to_profit
    json_path: $.policy_dependency.subsidy_to_profit
    type: decimal(8,4)
  # ... 更多字段
```

### 验收标准

- **AC1**: 增量同步
  - **Given** `ads_extracted_facts` 新增 5 条抽取结果
  - **When** 执行 `sync_facts_to_metrics.py --mode incremental`
  - **Then** `ads_company_metrics` 中对应的 5 条记录被插入或更新,同步耗时 ≤ 30 秒,字段映射完全符合 `metrics_mapping.yaml`

- **AC2**: 全量重建
  - **Given** Schema 升级,新增 `production_capacity_utilization` 字段
  - **When** 执行 `sync_facts_to_metrics.py --mode full --since 2023-01-01`
  - **Then** 宽表被完全重建,新字段对老数据为 NULL,新数据正确填充,重建过程不影响现有查询(用临时表切换)

- **AC3**: 跨版本兼容
  - **Given** `ads_extracted_facts` 同时存在 `schema_version=1` 和 `schema_version=2` 的数据
  - **When** 同步到宽表
  - **Then** 两个版本的数据都能被正确同步,新版本独有的字段只对 v2 数据填值,v1 数据该字段为 NULL,无报错

- **AC4**: 查询性能
  - **Given** 宽表已加载 200 只公司 × 5 年财报数据(约 4000 行)
  - **When** 执行"半导体设备行业研发占比 > 8% 且毛利率 > 30% 的公司"查询
  - **Then** 查询返回时间 ≤ 200ms

- **AC5**: 与原始层一致性
  - **Given** 任意公司的某一报告期数据
  - **When** 同时查询 `ads_extracted_facts` 的 JSON 字段和 `ads_company_metrics` 的对应字段
  - **Then** 两边数值完全一致,如果不一致触发告警(可能是同步遗漏或 JSON path 错误)
