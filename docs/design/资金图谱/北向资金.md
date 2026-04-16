# 资金获取方案: 北向资金 (配置盘 vs 交易盘)

## 底层数据
香港交易所 CCASS 持股数据。

## 托管行分类 (白名单)

### 配置类托管行
- HSBC Bank PLC
- JP Morgan Chase Bank
- Citibank N.A.
- Standard Chartered Bank
- Deutsche Bank AG
- BNP Paribas Securities Services

### 交易类托管行
- Goldman Sachs International
- Morgan Stanley & Co International
- UBS AG
- Barclays Capital Securities

## 计算公式
```
配置盘资金流 = Σ(配置类托管行_i 持股市值变化)
配置盘Score = (今日配置盘资金流 - 20日均值) / 20日标准差

交易盘资金流 = Σ(交易类托管行_i 持股市值变化)
交易盘Score = (今日交易盘资金流 - 20日均值) / 20日标准差

持股市值变化 = (今日持股数 - 昨日持股数) × 今日收盘价
```

## 数据获取方式
- HKEX 官网每日发布 (需爬虫): `https://www.hkexnews.hk/sdw/`
- 商业数据源: Wind 的“陆股通持股明细”、Choice 的“沪深港通持股”
- 第三方: 同花顺 iFinD、东方财富 Choice 均有现成接口

## 特殊处理
CCASS 数据按“参与者+股票代码”明细发布, 需要按托管行名称聚合, 并且需要排除发起人持股、法人持股等非陆股通持仓。这部分数据清洗工作量较大, 建议直接使用商业数据源。

## 显示规则与信号识别
系统应自动识别四种典型组合:

| 配置盘 | 交易盘 | 指示意义 |
|--------|--------|------|
| 绿(+) | 绿(+) | 共识看多, 趋势强化 |
| 绿(+) | 红(-) | 长线进场 vs 短线避险, **潜在底部信号** |
| 红(-) | 绿(+) | 长线撤退 vs 短线博弈, **潜在顶部信号** |
| 红(-) | 红(-) | 共识看空, 系统性下跌 |
