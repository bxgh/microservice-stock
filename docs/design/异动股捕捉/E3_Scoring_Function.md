# E3 · 综合评分函数

### E3-S1 评分公式

```text
composite_score = α · raw_score
                + β · score_l3_capital
                + γ · score_l4_emotion
                + ε · score_user_pref
                - ζ · score_dedup_penalty

权重(初始,可热配置):
  α = 0.40 (raw_score)
  β = 0.25 (L3 资金)
  γ = 0.15 (L4 情绪)
  ε = 0.10 (个人偏好)
  ζ = 0.10 (重复跟踪压制)

约束:
  - 各子项打分 ∈ [0, 100]
  - composite_score 计算后用 LEAST(100, GREATEST(0, x)) clamp
  - 权重读取自 dim_anomaly_score_weight WHERE is_active = 1
```

### E3-S2 子项打分细则

#### E3-S2-T1 `raw_score`(原始信号强度)

各 `pool_type` 的算法不同:

```yaml
strong 池:
  - 直接复用 ads_l8_stock_anomaly.attention_score(已是 0-100)

early 池:
  - 在各组合判定 SQL 中已计算(见 E2-S2-T1.5 等)
  - 各组合内部权重不同,确保跨组合可比

trap 池:
  - 高位出货:|intraday_drop_from_high| × 1000(放大到 0-100)
  - 假突破:跌破突破位百分比 × 800
  - 诱多放量:|drop_pct| × 1500
  - 领涨见顶:固定 70 分(或按近 5 日跌幅放大)
```

#### E3-S2-T2 `score_l3_capital`(L3 资金维度子分)

直接复用 L3 已计算的 `capital_score` + 个股维度调整:

```sql
-- 此 UPDATE 在所有 pool_type 行入库后执行
UPDATE ads_l8_unified_signal s
JOIN ads_l3_capital_flow c ON c.trade_date = s.trade_date
SET s.score_l3_capital = LEAST(100, GREATEST(0,
      0.6 * c.capital_score
    + 0.4 * (CASE
                WHEN s.main_net_inflow IS NULL THEN 50
                WHEN s.main_net_inflow > 0 THEN
                    LEAST(100, s.main_net_inflow / 100000000 * 20 + 50)
                ELSE
                    GREATEST(0, 50 + s.main_net_inflow / 100000000 * 20)
            END)
))
WHERE s.trade_date = @td;
```

#### E3-S2-T3 `score_l4_emotion`(L4 情绪维度子分)

不同池子用不同的情绪映射逻辑,**关键是 trap 池要反向**——情绪过热时,陷阱风险最高。

```sql
UPDATE ads_l8_unified_signal s
JOIN ads_l4_sentiment e ON e.trade_date = s.trade_date
SET s.score_l4_emotion = CASE
    -- strong/early 池:情绪好时加分
    WHEN s.pool_type IN ('strong', 'early')
        THEN e.profit_effect_score
    -- trap 池:情绪过热时加分(陷阱在情绪高位最危险)
    WHEN s.pool_type = 'trap' AND e.profit_effect_score > 70
        THEN LEAST(100, 80 + (e.profit_effect_score - 70))
    WHEN s.pool_type = 'trap'
        THEN e.profit_effect_score * 0.5
    ELSE 50
END
WHERE s.trade_date = @td;
```

#### E3-S2-T4 `score_user_pref`(个人板块偏好)

```sql
UPDATE ads_l8_unified_signal s
LEFT JOIN dim_user_sector_pref p
    ON p.user_id = 1
    AND p.is_active = 1
    AND p.sector_type = 'industry_sw1'
    AND p.sector_name = s.industry_sw1
SET s.score_user_pref = CASE
    WHEN p.weight IS NOT NULL THEN LEAST(100, 50 * p.weight)
    ELSE 50
END
WHERE s.trade_date = @td;
```

#### E3-S2-T5 `score_dedup_penalty`(重复跟踪压制)

```sql
UPDATE ads_l8_unified_signal s
SET s.score_dedup_pen = CASE
    WHEN EXISTS (
        SELECT 1 FROM ads_l8_unified_signal prev
        WHERE prev.ts_code = s.ts_code
          AND prev.trade_date BETWEEN DATE_SUB(@td, INTERVAL 7 DAY) AND DATE_SUB(@td, INTERVAL 1 DAY)
          AND prev.composite_score >= 60
    ) THEN 80
    ELSE 0
END
WHERE s.trade_date = @td;
```

### E3-S3 综合评分计算 SQL

```sql
-- 文件: sql/anomaly/06_composite_score.sql
-- 依赖: 上述 E3-S2 各 UPDATE 已执行完毕

UPDATE ads_l8_unified_signal s
JOIN dim_anomaly_score_weight w_a ON w_a.weight_key = 'alpha_raw_score'     AND w_a.is_active = 1
JOIN dim_anomaly_score_weight w_b ON w_b.weight_key = 'beta_l3_capital'     AND w_b.is_active = 1
JOIN dim_anomaly_score_weight w_g ON w_g.weight_key = 'gamma_l4_emotion'    AND w_g.is_active = 1
JOIN dim_anomaly_score_weight w_e ON w_e.weight_key = 'epsilon_user_pref'   AND w_e.is_active = 1
JOIN dim_anomaly_score_weight w_z ON w_z.weight_key = 'zeta_dedup_penalty'  AND w_z.is_active = 1
SET s.composite_score = LEAST(100, GREATEST(0,
      s.raw_score        * w_a.weight_value
    + s.score_l3_capital * w_b.weight_value
    + s.score_l4_emotion * w_g.weight_value
    + s.score_user_pref  * w_e.weight_value
    - s.score_dedup_pen  * w_z.weight_value
))
WHERE s.trade_date = @td;
```

### E3-S3-AC 综合评分整体验收

> **Given** 某股 7 日内已有过 composite_score=72 的强异动  
> **When** 当日再次产出该股的启动前异动  
> **Then** 当日 `score_dedup_pen = 80`,在 ζ=0.1 权重下,`composite_score` 被扣减 8 分
