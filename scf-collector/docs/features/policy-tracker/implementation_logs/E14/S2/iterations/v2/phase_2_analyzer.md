# E14-S2 Phase 2: Prompt 模板工程与 AI 政策分析引擎 (物理设计书)

本阶段聚焦于长文切片算法、场景化 Prompt 版本对齐、防崩溃 JSON 正则提取与 AI 分析核心主控逻辑。

## 1. 政策分类器 (PolicyClassifier) 与长文切片 (SegmentExtractor)
### 1.1 政策分类器设计
- 采取 **标题正则优先 + Flash 兜底分类** 混合算法。
- 提取 `ods_policy_info.title` 并与预设正则词汇对比：
  - “货币政策执行报告” → `monetary_policy_report`
  - “贷款市场报价利率” → `lpr_announcement`
  - “公开市场业务交易公告” → `open_market_op`
  - “中期借贷便利” → `mlf_op`
  - “国务院常务会议” → `executive_meeting`
- 若无正则命中，以 `deepseek-v4-flash` 进行一轮超低消耗的极简分类（限制 system message），将结果落入 `ods_policy_info.policy_type`。

### 1.2 关键段落提取器
对于数十万字的超长政策报告（如人行季度货币政策执行报告），强行全量传入 LLM 会导致成本失控与 SCF 内存溢出。
- **货政报告提取算法**：使用正则表达式匹配诸如 `(下一阶段主要政策思路|下一阶段主要政策措施)` 章节标题，截取到下一个同级标题（如“五、”或“第四部分”）前的内容。
- **政府工作报告提取**：匹配“宏观政策”、“货币政策”等小章节。
- **Fallback 保护**：若正则提取失败，提取头部前 4000 字与尾部最后 2000 字进行拼接，并在日志打印 WARN。

---

## 2. Prompt 注册中心与对齐设计
在 `shared/utils/prompts.py` 中：
- `GENERAL_SUMMARY_V2` 与 `WORDING_CONTRAST_V2` 全面升级，锁定包含 system message 与 2 组 high-quality few-shots。
- **缓存最大化对齐**：system message 内部不包含 any 动态变化变量（没有当前日期、UUID 或单次请求的 policy_id），保证 system message 的 hash 字节完全稳定，完美触发 DeepSeek 的 Prompt Caching 机制（极大地拉低计费成本）。

---

## 3. thinking 模式下的 JSON 防崩溃提取引擎
由于 `pro-thinking` 无法强制开启 `json_object`，大模型极易在返回的 JSON 外围包裹：
```markdown
```json
{
  "summary": ...
}
```
```
或者在 final response 的开头附带多余的引导词。
- **正则提取算法**：在 `PolicyAnalyzer` 中，使用 `re.search(r"\{.*\}", raw_content, re.DOTALL)` 正则匹配提取最外层的 `{}`，然后使用标准 `json.loads` 加载解析，强力杜绝 JSONDecodeError。

---

## 4. 同 Policy Type 上一期追溯算法
当遇到人行（`ts_code = 'PBC'`）或配置中开启了比对的政策时，执行以下 SQL 追溯历史基准：
```sql
SELECT *
FROM ods_policy_info
WHERE ts_code = :ts_code
  AND policy_type = :policy_type
  AND publish_date < :current_publish_date
  AND is_deleted = 0
ORDER BY publish_date DESC
LIMIT 1;
```
若基准不存在，自动退化为 `GENERAL_SUMMARY_V2` 的通用摘要模型，避免中断。

---

## 5. 行业匹配融合与 ORM 幂等落库
### 5.1 混合板块映射算法 (SectorMapper)
```
最终利好板块 = LLM 识别出来的板块 ∪ 关键词规则映射库 (dim_policy_keyword_sector)
```
- 读取政策原文，通过 SQL 查找命中的 `dim_policy_keyword_sector.keyword`。
- 将 LLM 解析出的板块与命中的维度表规则进行合并去重。
- 利好强度等级进行对齐（默认 3，规则匹配中可调优）。

### 5.2 ORM 幂等落库
使用 `aiomysql` 构建批量操作，利用 MySQL 联合唯一约束的 `ON DUPLICATE KEY UPDATE`：
```sql
INSERT INTO dwd_policy_analysis (policy_id, prompt_name, prompt_version, ...)
VALUES (...)
ON DUPLICATE KEY UPDATE 
    summary = VALUES(summary),
    importance_level = VALUES(importance_level),
    intensity_change = VALUES(intensity_change),
    cost_cny = VALUES(cost_cny),
    updated_at = CURRENT_TIMESTAMP;
```
同时写入 `dwd_policy_sector_impact` 扁平表，每次写入前先 `DELETE FROM dwd_policy_sector_impact WHERE policy_id = :policy_id AND analysis_id = :analysis_id` 确保数据不产生脏冗余。

---

## 6. 第二阶段验收指标 (AC)
- **AC2.1 (分类精准)**: 输入任意 LPR 公告能准确输出分类为 `lpr_announcement`。
- **AC2.2 (长文切片合格)**: 传入 4 万字货政报告，截取出来的 `segment_used` 处于 2000-8000 字之间。
- **AC2.3 (JSON 防崩溃可靠)**: 故意在 mock 的 API 响应中混入 Markdown 格式包装，分析器依然能够强力提纯并成功解析出 JSON 各项字段。
- **AC2.4 (板块排重)**: 验证 LLM 板块与关键词提取板块的去重融合运行通畅。
