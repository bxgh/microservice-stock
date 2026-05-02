# E4 · 每日 Top 10 推送规则

### E4-S1 配额分配

```yaml
配额(读取自 dim_anomaly_score_weight):
  pool_strong_quota: 4    # 强异动 4 条
  pool_early_quota:  4    # 启动前 4 条
  pool_trap_quota:   2    # 陷阱 2 条
  pool_trap_min:     1    # 陷阱保留最小名额
  total: 10
```

### E4-S2 动态填补规则

```text
执行顺序:
1. 各池按 composite_score DESC 取 quota 数量(同股票去重,取最高分信号)
2. 检查 trap 池实际取到数量
   - 若 trap 实际 < pool_trap_min(=1):
     - 从 trap 池(任何分数)再取 1 条凑足
     - 若 trap 池为空,则不补,接受当日不足 10 条
3. 计算缺额 = total - 已选数量
4. 缺额从未被选中的 strong/early 池(混合排序)按 composite_score DESC 填补
5. 标记 quota_slot:
   - 占用本池配额 → quota_strong / quota_early / quota_trap
   - 占用填补名额 → quota_filled
```

### E4-S3 Top 10 生成逻辑(Python)

```python
# 文件: scripts/anomaly/top10.py
# 在项目根目录执行: python -m scripts.anomaly.top10 --date 2026-05-02

import pandas as pd
from app.utils.db import get_engine

def generate_top10(trade_date: str):
    eng = get_engine()
    
    # 1. 读取配置
    cfg = pd.read_sql("""
        SELECT weight_key, weight_value 
        FROM dim_anomaly_score_weight 
        WHERE is_active = 1
    """, eng).set_index('weight_key')['weight_value'].to_dict()
    
    quotas = {
        'strong': int(cfg['pool_strong_quota']),
        'early':  int(cfg['pool_early_quota']),
        'trap':   int(cfg['pool_trap_quota']),
    }
    trap_min = int(cfg['pool_trap_min'])
    total = sum(quotas.values())
    
    # 2. 拉取当日全部信号(同股同池保留最高分)
    sql = """
        SELECT trade_date, ts_code, name, industry_sw1,
               pool_type, signal_type, signal_subtype, composite_score
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER(PARTITION BY ts_code, pool_type 
                                     ORDER BY composite_score DESC) AS rn
            FROM ads_l8_unified_signal
            WHERE trade_date = %s
        ) t WHERE rn = 1
    """
    # MySQL 5.7 无窗口函数,实际实现需要变量法或在 Python 侧 dedup
    df = pd.read_sql(sql, eng, params=(trade_date,))
    df = df.sort_values(['pool_type', 'composite_score'], ascending=[True, False])
    
    # 3. 各池按配额取
    selected = []
    for pool, q in quotas.items():
        sub = df[df['pool_type'] == pool].head(q).copy()
        sub['quota_slot'] = f'quota_{pool}'
        selected.append(sub)
    selected_df = pd.concat(selected) if selected else pd.DataFrame()
    
    # 4. 陷阱保底
    if (selected_df['pool_type'] == 'trap').sum() < trap_min:
        trap_extra = df[(df['pool_type'] == 'trap') 
                        & (~df['ts_code'].isin(selected_df['ts_code']))].head(1)
        if not trap_extra.empty:
            trap_extra = trap_extra.copy()
            trap_extra['quota_slot'] = 'quota_trap'
            selected_df = pd.concat([selected_df, trap_extra])
    
    # 5. 跨股票去重(防止同股同时在多池命中)
    selected_df = selected_df.sort_values('composite_score', ascending=False)
    selected_df = selected_df.drop_duplicates(subset='ts_code', keep='first')
    
    # 6. 填补缺额
    shortage = total - len(selected_df)
    if shortage > 0:
        candidates = df[~df['ts_code'].isin(selected_df['ts_code'])
                        & df['pool_type'].isin(['strong', 'early'])]
        candidates = candidates.sort_values('composite_score', ascending=False).head(shortage).copy()
        candidates['quota_slot'] = 'quota_filled'
        selected_df = pd.concat([selected_df, candidates])
    
    # 7. 排序并赋 rank_no
    final = selected_df.sort_values('composite_score', ascending=False).head(total).reset_index(drop=True)
    final['rank_no'] = range(1, len(final) + 1)
    
    # 8. 生成 headline 与 key_features(见 E4-S4)
    final['headline'] = final.apply(generate_headline, axis=1)
    final['key_features'] = final.apply(generate_key_features, axis=1)
    
    # 9. 写入 app_anomaly_top10_daily
    final.to_sql('app_anomaly_top10_daily', eng, if_exists='append', index=False)
```

### E4-S4 `headline` 与 `key_features` 生成

#### E4-S4-T1 headline 模板

```yaml
headline 模板(按 signal_type 套):
  early_combo_1:    "【龙头预备役】{name} 主力资金排名 {from}→{to},量能温和放大 {vol}× 维持 {days} 日"
  early_combo_2:    "【箱体蓄势】{name} {touches} 次测试 {price}元,均线粘合 {ma_pct}%"
  early_combo_3:    "【接力候选】{sector} 板块今日 {n} 只首板,{name} 振幅 {amp}% 未封板"
  early_combo_4:    "【底部反转】{name} 站稳年线 + 缩量回踩 + 板块估值低位"
  trap_lure_volume: "【诱多放量】{name} 昨日 {vol_ratio}× 拉升,今日跌破启动位 {drop}%"
  trap_false_breakout: "【假突破】{name} {n} 日前突破 {high} 元后未能站稳,今日收盘 {close} 元"
  trap_high_vol_topping: "【高位出货】{name} 当日 +{pct}% 后回落 {drop}%,量比 {vol}×"
  trap_leader_topping: "【领涨见顶】{name} 板块过去 20 日龙头,近 5 日跌 {ret_5d}% 但板块仍创新高"
  top_gainer:       "【涨幅榜】{name} 涨 +{pct}%,板高 {board_height}"
  top_loser:        "【跌幅榜】{name} 跌 {pct}%,主力净流出 {flow}万"
  high_turnover:    "【换手异动】{name} 换手 {tor}%,量比 {vol}×"
  volume_spike:     "【量能爆发】{name} +{pct}%,量比 {vol}×"
  breakout:         "【突破新高】{name} 突破 {days} 日新高 {price} 元"
  lhb:              "【龙虎榜】{name} 涨幅 +{pct}%,机构净买入 {buy}万"
```

#### E4-S4-T2 key_features 结构

```yaml
key_features JSON 示例:
  {
    "score_breakdown": {
      "raw":   75,
      "l3":    82,
      "l4":    65,
      "pref":  100,
      "dedup": 0
    },
    "signal_specifics": {
      "rank_jump_capital": "132 → 38",
      "vol_consistency":   "4 日",
      "sector_strength":   "TOP 22%"
    }
  }
```
