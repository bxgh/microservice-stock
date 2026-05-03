## E5 · 系统集成

### E5-S1 数据流向时间线

| 时间 | 步骤 | 操作 |
|---|---|---|
| 17:00 | 前置任务 | L1-L4 ETL 完成 |
| 17:15 | 前置任务 | L6-L8 ETL 完成 |
| 17:18 | **Step 1** | 派生指标层计算 (Derived Metrics) |
| 17:20 | **Step 2** | 市场状态判定 (Market State) |
| 17:22 | **Step 3** | 三池产出与标签判定 (Strong/Early/Trap) |
| 17:28 | **Step 4** | 多维印证计算 (Resonance/Counter/Temporal) |
| 17:30 | **Step 5** | 综合评分与中文说明生成 |
| 17:34 | **Step 6** | Top 10 推送生成 |
| 17:35 | **Step 7** | 前端拉取窗口开启 |

### E5-S2 任务编排配置 (JSON)

在 `post_market_def.json` 中定义新的 `anomaly_v11_pipeline` 步骤,确保任务依赖关系正确。

```json
{
  "step_id": "anomaly_v11_pipeline",
  "step_name": "异动扩展管线 v1.1",
  "depends_on": ["l8_anomaly", "l3_capital_flow", "l4_sentiment", "l6_event"],
  "tasks": [
    { "task_id": "compute_derived_metrics", "type": "python", "file": "scripts/anomaly/compute_derived_metrics.py" },
    { "task_id": "compute_market_state",    "type": "python", "file": "scripts/anomaly/compute_market_state.py" },
    { "task_id": "produce_strong_pool",     "type": "python", "file": "scripts/anomaly/produce_strong_pool.py" },
    { "task_id": "compute_early_combo1",    "type": "sql",    "file": "sql/anomaly/early_combo1.sql" },
    { "task_id": "compute_trap_signals",    "type": "python", "file": "scripts/anomaly/compute_trap.py" },
    { "task_id": "compute_tags",            "type": "python", "file": "scripts/anomaly/compute_tags.py" },
    { "task_id": "compute_score_composite", "type": "sql",    "file": "sql/anomaly/composite_score.sql" },
    { "task_id": "generate_top10",          "type": "python", "file": "scripts/anomaly/top10.py" }
  ]
}
```

### E5-S3 与下游系统接口

#### 观察点系统消费方式
- **触发源**: 每日读取 `app_anomaly_top10_daily`。
- **关联**: 通过 `signal_id` 关联回 `ads_l8_unified_signal` 获取详细标签云及共振详情。
- **传递**: 将 `explanation_zh` 与 `key_features` 传递至观察点的前端 UI。
- **反馈**: 观察点系统记录用户的"接受/忽略"行为,为后续 v1.2 的命中率自学习模型提供标注数据。
