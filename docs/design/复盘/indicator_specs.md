# E2: 派生指标输出规范

> 指标按 9 层观察层组织。涨跌幅以小数表示(0.0123 = 1.23%)。

## L1: 市场全景指标 **[已实现]**

- **turnover_total**: 全市场成交额
- **up_count / down_count**: 涨跌家数
- **market_breadth**: 市场宽度 (上涨家数 / 总家数) **[已实现]**
- **monitor_health_score**: 综合健康度得分 **[已实现]**

---

## L2: 结构分化指标 **[部分已实现]**

- **industry_dispersion**: 行业分化度 (截面标准差) **[已实现]**
- **growth_value_ratio**: 成长/价值相对强度 **[已实现]**
- **large_vs_small**: 大小盘强弱 **[待开发]**
- **momentum_factor**: 20日动量因子 **[待开发]**

---

## L3: 资金层指标 **[部分已实现]**

- **north_funds_momentum**: 北向资金 10 日动能得分 **[已实现]**
- **lhb_net_buy_score**: 龙虎榜净买入得分 **[已实现]**
- **block_trade_score**: 大宗交易得分 **[已实现]**
- **margin_buy_score**: 融资买入得分 **[已实现]**
- **etf_huijin_signal**: 国家队 ETF 异常申购信号 **[待开发]**
- **index_futures_basis**: 期指年化基差 **[待开发]**

---

## L4: 情绪层指标 **[待开发]**

- **max_board_height**: 最高板高度
- **board_ladder**: 连板梯队 (如 10-5-3-2-1 分布)
- **promotion_rate**: 各板晋级率
- **yesterday_zt_avg_return**: 昨日涨停今日平均涨幅
- **profit_effect_score**: 综合赚钱效应得分

---

## L5: 估值层指标 **[待开发]**

- **pe_pctile_10y / pb_pctile_10y**: 指数/行业 10 年估值分位
- **erp_wind_a**: 万得全 A 风险溢价 (ERP)
- **valuation_signal**: 低估/合理/高估判断

---

## L6: 基本面与公告指标 **[待开发]**

- **yjyg_magnitude**: 业绩增长量级
- **jiejin_market_value**: 未来 30 天解禁市值
- **attention_score**: 公告次日关注度评分

---

## L7: 跨市场指标 **[待开发]**

- **hstech_pct**: 恒生科技涨跌幅
- **usdcny_diff**: 在离岸汇率价差
- **cn_us_10y_spread**: 中美利差

---

## L8: 异动与个股指标 **[待开发]**

- **anomaly_type**: 爆量突破 / 极致缩量 / 均线多头等信号
- **lhb_flag**: 是否上榜

---

## L9: 次日决策准备 **[待开发]**

- **hot_themes_today**: 今日强势主线
- **watchlist_next_day**: 次日重点观察标的
- **market_summary_text**: 自动化复盘文案
