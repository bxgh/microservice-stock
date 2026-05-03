## E4 · Top 10 推送规则

### E4-S1 推送生成流程

每日 17:34 执行 Top 10 推送管线,核心逻辑如下:

1.  **读取 Profile**: 加载用户当前激活的筛选模板 (默认/短线/中线等)。
2.  **筛选候选**:
    - 仅保留 `default_visible=1` 的记录。
    - 应用 Profile 中定义的 `exclude_tags` (如排除 ST、次新)。
    - 应用 `min_resonance` 等级过滤。
3.  **偏好加权**:
    - 如果命中 Profile 中的 `prefer_tags` (如板块龙头),则评分乘以 `boost_factor`。
4.  **L5 共振必入**:
    - L5 等级信号具有最高优先级,但每类池子最多占 3 条名额。
5.  **池化配额分配**:
    - **Strong 池**: 4 条。
    - **Early 池**: 4 条。
    - **Trap 池**: 2 条。
6.  **动态填补与保底**:
    - 若某池数量不足,由其他池高分项填补。
    - **陷阱保底**: 即便陷阱池记录较少,也至少保留 1 个名额 (除非当日无陷阱信号)。
7.  **跨池去重**:
    - 确保同一股票在当日推送清单中仅出现一次 (保留最高分记录)。

### E4-S2 核心实现 (Python 代码框架)

```python
def generate_top10(trade_date: str, user_id: int = 1):
    # 1. 获取激活 Profile 与 评分权重配置
    profile = get_active_profile(user_id)
    weights = get_active_weights()
    
    # 2. 拉取当日候选信号并进行初步过滤 (exclude_tags)
    df = load_candidates(trade_date, profile)
    
    # 3. 计算加权评分 (adjusted_score)
    df['adjusted_score'] = apply_boost(df, profile)
    
    # 4. 依次选取 L5 必入项、各池配额项
    selected = select_by_quotas(df, profile, weights)
    
    # 5. 生成 Headline 与 Key Features
    final_list = enrich_metadata(selected)
    
    # 6. 写入 app_anomaly_top10_daily
    save_to_db(final_list)
```

### E4-S3 展示字段约定

-   **Headline**: 根据 `signal_type` 生成的精简标题(如:【龙头预备役】寒武纪 主力资金排名 132→38)。
-   **Key Features (JSON)**:
    - `score_breakdown`: 展示各子项打分细节。
    - `resonance_level`: 共振等级。
    - `top_tags`: 提取前 5 个最显著标签用于前端 Tag 展示。
