# 附录

## 附录 A · 信号类型字典

### A.1 strong 池(`pool_type='strong'`)

| `signal_type` | 中文 | 数据源 | 触发条件 |
|---|---|---|---|
| `top_gainer` | 涨幅榜 | L8 | `pct_chg` 排名前 N |
| `top_loser` | 跌幅榜 | L8 | `pct_chg` 排名后 N |
| `high_turnover` | 换手异动 | L8 | 换手率 > 20 日均 ×3 且 ≥ 10% |
| `volume_spike` | 量能爆发 | L8 | 量比 ≥ 3 且涨幅 ≥ 5% |
| `breakout` | 突破新高 | L8 | 收盘 ≥ 60/120/250 日最高 |
| `lhb` | 上龙虎榜 | L8 | 出现在 `stock_lhb_daily` |

#### A.1.1 strong 池 `signal_features` JSON 字段

```yaml
{
  "board_height":   <int>,        # 连板高度,首板=1
  "is_one_word":    <0|1>,        # 一字板
  "lhb_yz_buy":     <number>,     # 龙虎榜游资买入金额
  "breakout_days":  <int>,        # 突破多少日新高
  "has_event":      <0|1>         # 当日是否有公告
}
```

### A.2 early 池(`pool_type='early'`)

| `signal_type` | `signal_subtype` | 中文 | 优先级 |
|---|---|---|---|
| `early_combo_1` | `leader_candidate` | 龙头预备役 | ⭐ 第 1 |
| `early_combo_3` | `relay_candidate` | 连板接力候选 | ⭐ 第 2 |
| `early_combo_2` | `box_breakout_pending` | 箱体突破前蓄势 | ⭐ 第 3 |
| `early_combo_4` | `trend_reversal_early` | 趋势反转早期 | ⭐ 第 4 |

#### A.2.1 early 池 `signal_features` JSON 字段

```yaml
# 组合 1
{
  "rank_jump_capital":   {"from": <int>, "to": <int>},
  "rank_jump_industry":  {"from": <float>, "to": <float>},
  "vol_consistency_days": <int>,
  "has_announcement":    0,
  "sector_5d_rank_pct":  <float>
}

# 组合 2
{
  "resistance_level":    <number>,
  "box_test_count":      <int>,
  "ma_convergence":      <float>,
  "turnover_acceleration": <float>
}

# 组合 3
{
  "sector_firstboard_count": <int>,
  "amplitude":               <float>,
  "sector_5d_rank_pct":      <float>,
  "main_net_inflow":         <number>
}

# 组合 4
{
  "t0_date":             "<YYYY-MM-DD>",
  "ma250_at_t0":         <number>,
  "pe_ttm_pctile_t0":    <float>,
  "verify_pass":         1
}
```

### A.3 trap 池(`pool_type='trap'`)

| `signal_type` | `trap_subtype` | 中文 | 判定时机 |
|---|---|---|---|
| `trap_lure_volume` | `lure_volume` | 诱多放量 | T+1 |
| `trap_false_breakout` | `false_breakout` | 假突破 | T+2 |
| `trap_high_vol_topping` | `high_vol_topping` | 高位巨量出货 | T+0 |
| `trap_leader_topping` | `leader_topping` | 领涨股见顶 | T+0 |

#### A.3.1 trap 池 `signal_features` JSON 字段

```yaml
# 诱多放量
{
  "trap_subtype":     "lure_volume",
  "lure_high_close":  <number>,
  "today_close":      <number>,
  "drop_pct":         <float>,
  "lure_vol_ratio":   <float>
}

# 假突破
{
  "trap_subtype":         "false_breakout",
  "breakout_date":        "<YYYY-MM-DD>",
  "breakout_high":        <number>,
  "today_close":          <number>,
  "below_breakout_pct":   <float>
}

# 高位出货
{
  "trap_subtype":              "high_vol_topping",
  "intraday_drop_from_high":   <float>,
  "vol_ratio_today":           <float>,
  "cumulative_60d_pct":        <float>
}

# 领涨见顶
{
  "trap_subtype":         "leader_topping",
  "sector_20d_rank":      1,
  "stock_5d_pct":         <float>,
  "sector_at_5d_high":    1
}
```

---

## 附录 B · 权重调优指南

### B.1 何时调优

- **触发条件 1**:上线满 1 个月,有足够样本
- **触发条件 2**:观察期内某项度量指标显著偏离目标值
- **触发条件 3**:用户反馈 Top 10 推送质量明显异常(如全是强异动、启动前从不上榜)

### B.2 调优方法

#### B.2.1 经验调整(简单)

观察 1 个月推送数据,人工判断哪个维度被低估或过度强调,微调权重(每次调整幅度 ≤ 0.05)。

#### B.2.2 命中率反推(进阶,需观察点系统上线后)

待观察点系统积累足够命中率数据后:

```text
1. 按 signal_type 聚合命中率
2. 高命中率 signal_type → 提高其 raw_score 权重
3. 命中率与 capital_score 强相关 → 提高 β 权重
4. 反之降低
```

### B.3 调优执行步骤

```bash
# 1. 在数据库中新建一个版本
INSERT INTO dim_anomaly_score_weight (version, weight_key, weight_value, ...)
VALUES ('v20260601', 'alpha_raw_score', 0.45, ...);

# 2. 生效新版本(原版本设为 inactive)
UPDATE dim_anomaly_score_weight SET is_active = 0 WHERE version = 'v20260502';
UPDATE dim_anomaly_score_weight SET is_active = 1 WHERE version = 'v20260601';

# 3. 重跑历史(可选)
python -m scripts.anomaly.recompute --start 2026-05-02 --end 2026-05-31

# 4. 对比新旧版本下的 Top 10 差异
python -m scripts.anomaly.compare_versions --v_old v20260502 --v_new v20260601
```

### B.4 调优记录

每次调优需在文档中追加记录:

| 版本 | 生效日期 | 调整内容 | 调整理由 | 评估结果 |
|---|---|---|---|---|
| v20260502 | 2026-05-02 | 初始版本 | - | - |
| TBD | TBD | TBD | TBD | TBD |
