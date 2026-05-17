# E14-S2 Phase 3: SCF 函数异步化拆分与分发预警 (物理设计书)

本阶段聚焦于彻底防范 SCF 超时的三函数物理隔离解耦、轻量级异步状态机队列，以及重要政策的高品质预警模板设计。

## 1. SCF 目录重构与文件划分
废弃原单体同步文件，建立物理上的三个子函数工程文件夹：

```
scf-collector/functions/
├── policy_collector/
│   ├── index.py          # 采集触发入口 (定时器: 每30分钟运行)
│   └── config.json       # 配置探测
├── policy_analyzer/
│   ├── index.py          # AI 分析入口 (定时器: 每5分钟运行)
│   └── config.json       
└── policy_notifier/
    ├── index.py          # 通知分发入口 (定时器: 每15分钟运行)
    └── config.json       
```
通过 `docker-compose.yml` 或 `serverless.yml` 独立对其配置定时触发器。

---

## 2. 基于 MySQL 的轻量级异步状态队列
不引入 CMQ/Kafka 等复杂中间件。通过 `ods_policy_info.analysis_status` 字段流转作为队列基础。

### 2.1 任务领取与并发互斥锁
防范 SCF 并发调度导致同一政策被多个实例重复调用大模型：
1. `policy_analyzer` 启动时，开启数据库事务：
   ```sql
   -- 1. 批量锁定待处理数据
   UPDATE ods_policy_info
   SET analysis_status = 'analyzing'
   WHERE analysis_status = 'pending_analysis'
     AND is_deleted = 0
   ORDER BY publish_date DESC
   LIMIT 5;
   ```
2. 随后，仅读取已被修改为 `analyzing` 的数据进行处理，处理完毕后统一置为 `analyzed`。这利用了 MySQL 5.7 原生行级锁与并发隔离，极度安全。

---

## 3. 自研 JSON 状态流水契约 (JSON Pipeline Contract)

每个云函数完成运行前，**必须**将本次的统计明细序列化为标准化 JSON 并调用 `log_pipeline_run_v2` 写入 `meta_pipeline_run.output_summary` 中。

### 3.1 Collector (采集器) 流水契约
- **Pipeline ID**: `policy_collector`
- **JSON Contract 结构**:
```json
{
  "new_policies_fetched": 3,
  "sources_scanned": ["PBC", "CSRC", "GOV"],
  "fetched_details": [
    {"ts_code": "PBC", "title": "2025年第四季度中国货币政策执行报告"},
    {"ts_code": "CSRC", "title": "关于进一步规范股份减持行为的通知"}
  ],
  "status": "SUCCESS"
}
```

### 3.2 Analyzer (分析器) 流水契约
- **Pipeline ID**: `policy_analyzer`
- **JSON Contract 结构**:
```json
{
  "policies_processed": 5,
  "success_count": 5,
  "failure_count": 0,
  "details": [
    {
      "policy_id": 1024,
      "ts_code": "PBC",
      "model_used": "deepseek-v4-pro",
      "thinking_enabled": true,
      "cost_cny": 0.045230,
      "intensity_change": "增强"
    }
  ],
  "total_tokens": {
    "input_cache_hit": 12000,
    "input_cache_miss": 4000,
    "output": 850,
    "reasoning": 1500
  },
  "total_cost_cny": 0.082410,
  "status": "SUCCESS"
}
```

### 3.3 Notifier (通知器) 流水契约
- **Pipeline ID**: `policy_notifier`
- **JSON Contract 结构**:
```json
{
  "notified_count": 2,
  "notified_details": [
    {"policy_id": 1024, "importance_level": 5, "pushed_channels": ["WeChat", "Email"]}
  ],
  "channels_summary": {
    "wechat_pushes": 1,
    "email_pushes": 1
  },
  "status": "SUCCESS"
}
```

---

## 4. 高品质分发通知渲染
### 4.1 微信通知格式
微信限制纯文本，限制在 600 字符内，突出星级与强度变化。

### 4.2 高品质 HTML 邮件样式设计
- **色调风格**：采用符合金融专业投研的高级深色/浅色高亮卡片（Glassmorphism 或简约无框白）。
- **措辞比对卡片**：
  - 若 `intensity_change = '增强'`，以红色前缀突出 `🔼 强度增强`；
  - 若为 `减弱`，以蓝色前缀突出 `🔽 强度减弱`；
  - 若为 `持平`，展示为 `持平`。
- **差异对照表**：
  - 以高亮灰色背景呈现表格，清晰对照“上一期表述”与“本期新变动”，方便投资经理秒读增减字细节。

---

## 5. 第三阶段验收指标 (AC)
- **AC3.1 (隔离分治)**: 手动启动 `policy_collector` 收集 10 条数据置为 `pending_analysis`。启动 `policy_analyzer` 仅读取前 5 条并加锁为 `analyzing`，其他数据状态保持不动。
- **AC3.2 (状态流水达标)**: 三个云函数运行后，其在 `meta_pipeline_run.output_summary` 中产生的 JSON 流水完全符合上述 3.1、3.2、3.3 小节的契约架构定义。
- **AC3.3 (邮件渲染无失真)**: 收到 Staging 环境测试邮件，排版布局优雅，在手机与 PC 邮箱端均无任何失真。
