# 第 2 章 · API 接口契约 (E3)

## E3-S1: L2 结构分化总接口

**Endpoint**: `GET /api/v1/dashboard/l2`
**Params**: `date` (YYYY-MM-DD, 可选, 默认最新)

### 成功返回 (200 OK)

```json
{
  "trade_date": "2026-04-25",
  "industry": {
    "top5": [
      {
        "rank": 1,
        "code": "801080.SI",
        "name": "电子",
        "pct": 0.0345,
        "leader_name": "贵州茅台",
        "heat_label": "hot"
      }
    ],
    "bottom5": [],
    "heatmap": [
      {
        "name_short": "电子",
        "pct": 0.0345,
        "bg_color": "#FF0000"
      }
    ]
  },
  "style": {
    "factors": [
      {
        "code": "large_vs_small",
        "name": "大小盘",
        "long_name": "沪深 300",
        "short_name": "中证 2000",
        "spread": 0.0208,
        "direction": "long_dominant"
      }
    ]
  },
  "concept": {
    "top10": [
      {
        "rank": 1,
        "name": "人形机器人",
        "pct": 0.0523,
        "limit_up_count": 8,
        "constituent_count": 45,
        "theme_label": "main_theme"
      }
    ]
  }
}
```

### 字段映射说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `pct` | Decimal | 涨跌幅小数,前端需转百分比 |
| `heat_label` | Enum | `hot` / `warm` / `normal` / `cold` |
| `direction` | Enum | `long_dominant` (多头占优) / `short_dominant` (空头占优) |
| `theme_label` | Enum | `main_theme` (主线) / `one_day` (一日游) 等 |
