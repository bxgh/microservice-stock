# Epic 14 Story 1 宏观与监管政策多源联合探测采集层完工阶段性总结

总结宏观政策多源联合数据采集层 (Path A) 的核心交付物、落地数据库结构、数据质量控制(QC)流程及自动化测试通过指标。

---

## 1. 核心交付物一览

在 Epic 14 Story 1 阶段，我们成功构建了支持多源高容错探测的监管政策采集层，彻底实现了无封锁抓取：

* **动态 WAF 绕道抓取器 (`GovCollector`)**: 支持抓取 `gov.cn` 全量历史和最新 JSON 列表，通过对详情页发文机关的 BeautifulSoup 元数据定位，将包含 `中国人民银行`、`中国证券监督管理委员会` 的政策记录分别重映射至分类 `PBC` 和 `CSRC`。
* **高频直连 API 抓取器 (`CsrcCollector`)**: 成功逆向出证监会官方 `csrc.gov.cn` 开放 JSON 查询接口，实现了高频、轻量级的直连增量同步，将 `ts_code` 落地为 `CSRC`。
* **多通道预警分发系统 (`index.py`)**: 并联串联执行以上两路 Collector，对新录入政策实时发出含精确来源统计的微信（Server酱）和 SMTP 邮件格式警报。

---

## 2. 数据库落子证明 (True Source Status)

采集系统已于隔离测试环境和真实连接下顺利落地 1,061 条宏观与监管核心数据：

```sql
-- 统计数据库中当前各分类政策数据行数
SELECT ts_code, COUNT(*), MIN(publish_date), MAX(publish_date)
FROM ods_policy_info
GROUP BY ts_code;

+---------+----------+-------------------+-------------------+
| ts_code | COUNT(*) | MIN(publish_date) | MAX(publish_date) |
+---------+----------+-------------------+-------------------+
| GOV_CN  |     1046 | 2023-01-01        | 2026-05-16        |
| CSRC    |       15 | 2025-04-18        | 2026-05-15        |
+---------+----------+-------------------+-------------------+
```

---

## 3. 质量控制与数据防御 (QC & Robustness)

我们实施了严格的**数据防重与生命周期审计**规则以保持高数据清洁度：
1. **URL 一级指纹去重**: 使用 `source_url` 的 UNIQUE KEY 作为主去重手段，保障网络连接与重试时的首要防线。
2. **MD5 二级内容去重**: 抓取正文后计算全文本的 MD5 摘要，对于相同内容但 URL 变动的网页（如临时镜面页面）起到二级防御阻断，保证 `ods_policy_info` 表行绝对无冗余。
3. **安全三件套对齐**: 每行数据物理落地时自动对齐 `created_at`、`updated_at` 与软删除字段 `is_deleted`，符合 `AGENTS.md` 的系统级安全性门禁要求。

---

## 4. 自动化测试指标

已实现包含 Mock 网络环境在内的 3 大完整异步集成用例：
* **`test_csrc_collector_parse_list`**: 验证证监会 JSON 数据列表的序列化与格式标准化。
* **`test_csrc_collector_parse_detail`**: 验证证监会详情正文 `.content` 的提取准确度。
* **`test_gov_collector_agency_mapping`**: 验证中国政府网详情元数据表在 `中国人民银行`、`中国证券监督管理委员会` 和 `国务院` 三种情境下的 `ts_code` 重映射是否精准符合预期。

> **测试执行命令**: `python tests/test_policy_collector.py` (OK, 3 Tests Passed)
