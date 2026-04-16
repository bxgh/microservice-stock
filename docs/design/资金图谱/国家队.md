# 资金获取方案: 国家队

## 底层数据
五只汇金系ETF的日度份额变化。

## 重点ETF清单
- 510300 (华泰柏瑞沪深300ETF)
- 510310 (易方达沪深300ETF)
- 510330 (华夏沪深300ETF)
- 159919 (嘉实沪深300ETF)
- 510050 (华夏上证50ETF)
- 510500 (南方中证500ETF)
- 159922 (嘉实中证500ETF)
- 159845 (华夏中证1000ETF)

## 计算公式
```
NationalTeam_NetFlow = Σ(ETF_i份额变化 × ETF_i单位净值)
NationalTeam_Score = (今日NetFlow - 60日均值) / 60日标准差
```

## 数据源
- 上交所: `http://www.sse.com.cn/market/fund/disclose/netvalue/`
- 深交所: `http://www.szse.cn/disclosure/fund/`
- 简化: akshare 的 `fund_etf_fund_daily_em()` 接口

## 显示规则
- Score > +1σ: 温度计绿色向右, 大资金买入
- Score < -1σ: 温度计红色向左, 大资金卖出
- |Score| > 2σ: 闪烁警示, 异常流入流出

## 特殊提示
国家队的特点是“低频但巨大”。日常多数时候温度计在中性区域, 偶尔出现极端值。当出现 >2σ 的正向流入时, 系统应弹出醒目提示, 因为这通常是关键信号。
