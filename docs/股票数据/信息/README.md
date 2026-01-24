# 信息维度 (Information Dimension)

负责量化市场预期、机构态度及散户热度。

## 1. 核心指标

| 指标 | 代码 | 定义 | 来源 |
| :--- | :--- | :--- | :--- |
| **机构评级** | $I_{analyst}$ | 机构买入/增持评级数量及变动方向 | AkShare (`stock_em_analyst_rank`) |
| **业绩预期** | $I_{forecast}$ | 业绩预告的预增幅度 | AkShare (`stock_em_yjyg`) |
| **市场热度** | $I_{buzz}$ | 股吧发帖量与阅读量的统计特征 | AkShare (`stock_comment_em`) |

## 2. API 接口

### 2.1 机构评级
- **同步**: `POST /api/v1/information/analyst-ranks/sync`
- **查询**: `GET /api/v1/information/analyst-ranks/{code}`

### 2.2 业绩预告
- **同步**: `POST /api/v1/information/forecasts/sync`
- **查询**: `GET /api/v1/information/forecasts/{code}`

### 2.3 市场热度
- **同步**: `POST /api/v1/information/sentiment/sync`
- **查询**: `GET /api/v1/information/sentiment/{code}`

## 3. 数据库表

- `stock_analyst_rank`: 机构评级明细
- `stock_performance_forecast`: 业绩预告
- `stock_sentiment_daily`: 每日热度统计

详见 [五维度数据库结构](../五维度数据库结构.md)
