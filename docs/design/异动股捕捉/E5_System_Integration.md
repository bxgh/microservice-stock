# E5 · 系统集成

### E5-S1 数据流向

```text
17:00  L1/L2/L3/L4 ETL 完成 (现有调度)
17:15  L6/L7/L8 ETL 完成   (现有调度)
       ↓
17:20  [新增] 同步 L8 strong → ads_l8_unified_signal
17:22  [新增] 计算 L8.5 early(组合 1/2/3/4)
17:25  [新增] 计算 L8.6 trap(诱多/假突破/高位出货/领涨见顶)
17:27  [新增] 综合评分计算(应用权重)
17:29  [新增] 生成 app_anomaly_top10_daily
17:30  推送窗口开启 (前端拉取)
```

### E5-S2 任务编排

在 `post_market_def.json`(现有调度配置)中新增 step:

```json
{
  "step_id": "anomaly_extended_pipeline",
  "step_name": "异动扩展管线",
  "depends_on": ["l8_anomaly", "l3_capital_flow", "l4_sentiment", "l6_event"],
  "tasks": [
    { "task_id": "sync_l8_strong",         "type": "sql",    "file": "sql/anomaly/01_sync_strong.sql" },
    { "task_id": "compute_early_combo1",   "type": "sql",    "file": "sql/anomaly/02_combo1.sql" },
    { "task_id": "compute_early_combo2",   "type": "python", "file": "scripts/anomaly/combo2.py",
      "note": "形态判定 SQL 复杂,Python 实现" },
    { "task_id": "compute_early_combo3",   "type": "sql",    "file": "sql/anomaly/04_combo3.sql" },
    { "task_id": "compute_early_combo4",   "type": "python", "file": "scripts/anomaly/combo4.py",
      "note": "跨日候选追踪,需 Python" },
    { "task_id": "compute_trap_lure",      "type": "sql",    "file": "sql/anomaly/05_trap_lure_volume.sql" },
    { "task_id": "compute_trap_false_bo",  "type": "sql",    "file": "sql/anomaly/05_trap_false_breakout.sql" },
    { "task_id": "compute_trap_topping",   "type": "sql",    "file": "sql/anomaly/05_trap_high_vol_topping.sql" },
    { "task_id": "compute_trap_leader",    "type": "python", "file": "scripts/anomaly/trap_leader_topping.py" },
    { "task_id": "compute_score_l3",       "type": "sql",    "file": "sql/anomaly/06a_score_l3.sql" },
    { "task_id": "compute_score_l4",       "type": "sql",    "file": "sql/anomaly/06b_score_l4.sql" },
    { "task_id": "compute_score_pref",     "type": "sql",    "file": "sql/anomaly/06c_score_pref.sql" },
    { "task_id": "compute_score_dedup",    "type": "sql",    "file": "sql/anomaly/06d_score_dedup.sql" },
    { "task_id": "compute_composite_score","type": "sql",    "file": "sql/anomaly/06e_composite.sql" },
    { "task_id": "generate_top10",         "type": "python", "file": "scripts/anomaly/top10.py" }
  ],
  "schedule": "17:20",
  "timeout_minutes": 15
}
```

### E5-S3 与下游观察点系统的接口

```yaml
观察点系统消费方式:
  - 读取 app_anomaly_top10_daily WHERE trade_date = @td
  - 用户对每条记录可"接受 → 转为观察点"或"忽略"
  - 接受后,signal_type / signal_features 作为观察点的"触发上下文"传入
  - 后续观察点系统的「观测对象」「假设」「主观表态」基于此构建
  - 接口字段:
      ts_code, name, industry_sw1, pool_type, signal_type,
      signal_subtype, composite_score, headline, key_features
```
