# Implementation Plan - E14-S1: Data Acquisition Layer (Path A Expansion)

横向扩展宏观政策自动化采集层，实现对中国政府网（Gov.cn）、中国人民银行（PBC/央行）、中国证监会（CSRC/证监会）的精准监控与去重落库。

## 1. Readiness Check (AGENTS.md)

- [x] **需求解析**: 
  1. **证监会数据源 (CSRC)**：利用新挖掘的官方 `/searchList` JSON 接口（无 WAF 拦截），编写专用的 `CsrcCollector`，抓取高密度的资本市场监管通告与规章。
  2. **央行数据源 (PBC)**：鉴于人行官网设有强力安全 WAF（动态 JS Cookie），采用高容错的 **中央政策库聚合解析方案**。更新 `GovCollector`，在抓取详情页时，动态解析顶部元数据表中的 `发文机关` 字段。若属于 "中国人民银行" 或 "中国证监会"，则将 `ts_code` 动态归属为 `PBC` 或 `CSRC`。
  3. **去重与入库**：保留现有的 URL/MD5 双重去重机制，自动关闭连接池。
- [x] **依赖认证**: 
  - **数据库**：已完成 `ods_policy_info` 建表与 1046 条历史数据回填。
  - **分支与环境**：保持在 `feat/e14-policy-tracker` 分支上开发。
- [x] **角色激活**: 
  - `[Back-end Engineer]`：负责异步采集爬虫编写。
  - `[Data Quality Steward]`：负责字段识别与双源合并去重校验。

---

## 2. 详细技术方案

### 2.1 GovCollector 增强（动态机构归属）
在 [gov_collector.py](file:///e:/gitee/microservice-stock/scf-collector/shared/collectors/policy/gov_collector.py) 中：
1. 抓取正文时，解析第一张 `<table>`（元数据表）。
2. 定位文本包含 `"发文机关："` 的单元格，获取其邻近单元格的内容。
3. 动态判定归属：
   - 包含 "人民银行" -> `ts_code = "PBC"`
   - 包含 "证监会" -> `ts_code = "CSRC"`
   - 其他 -> `ts_code = "GOV_CN"`

### 2.2 CSRC 独立采集器（CsrcCollector）
在 `scf-collector/shared/collectors/policy/` 下新建 [csrc_collector.py](file:///e:/gitee/microservice-stock/scf-collector/shared/collectors/policy/csrc_collector.py)：
1. **接口地址**：`http://www.csrc.gov.cn/searchList/cd11df89f5894c1eac37ae37cc11e369?_isAgg=true&_isJson=true&_pageSize=15&page=1`。
2. **逻辑**：
   - 定时拉取 JSON 最新页，解析 `title`、`url`、`publishedTimeStr` 等字段。
   - 详情正文解析：请求详情页面，提取元素 `.content` 下的干净文本。
   - 计算内容 MD5，写入 `ods_policy_info` 时设定 `ts_code = "CSRC"`。

### 2.3 入口函数整合
修改 [index.py](file:///e:/gitee/microservice-stock/scf-collector/functions/policy_monitor/index.py)：
- 导入 `GovCollector` 与 `CsrcCollector` 并行异步执行，汇总新增条数，合并分发预警通知。

---

## 3. 拟修改与新增文件清单

#### [MODIFY] [gov_collector.py](file:///e:/gitee/microservice-stock/scf-collector/shared/collectors/policy/gov_collector.py)
- 增强 `fetch_detail` 方法，返回 `(content_text, ts_code)` 元组。
- 修改 `run` 逻辑，入库时采用动态解析出的 `ts_code`。

#### [NEW] [csrc_collector.py](file:///e:/gitee/microservice-stock/scf-collector/shared/collectors/policy/csrc_collector.py)
- 实现证监会专属的 JSON API 抓取适配器与详情解析逻辑。

#### [MODIFY] [index.py](file:///e:/gitee/microservice-stock/scf-collector/functions/policy_monitor/index.py)
- 整合 `GovCollector` 和 `CsrcCollector` 运行流程。

---

## 4. 验证计划

### 自动化测试
- 在 `tests/test_policy_collector.py` 中编写集成测试：
  - 模拟测试 `CsrcCollector` 获取 JSON 列表并能解析出详情页的正文。
  - 模拟测试 `GovCollector` 在面对包含 "发文机关：中国人民银行" 网页时的机构提取逻辑。

### 手动验证
- 运行测试入口，观察 `ods_policy_info` 表中的 `ts_code` 是否成功出现 `PBC` 与 `CSRC`。
- 确认多渠道推送正常触发且标题格式正确。

---

> [!IMPORTANT]
> **评审意见征集**：
> 请核对上述横向扩展方案，若无问题，请回复「同意」以授权我开始实施代码开发。
