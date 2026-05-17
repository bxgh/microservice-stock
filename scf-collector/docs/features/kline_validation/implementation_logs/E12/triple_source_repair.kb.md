# A股盘后数据自愈修复与三级校验最佳实践

> [!TIP]
> 本文档沉淀了 Epic E12 研发过程中总结出的系统级最佳实践（Best Practices）与核心技巧，为未来的数据同步系统设计提供高复用资产。

---

## 1. 理论空洞审计：笛卡尔积真源计算法

在对账全市场数据完备性时，最忌讳使用“单股回填”对账，效率低下。我们提炼了 **“笛卡尔积完备性审计法”**：
1. **理论总量 (Cartesian Product)**：交易日历中所有已开盘日期 $\times$ 股票名单中在该日期已上市且未退市的个股。
2. **高效查询**：在 SQL 层执行 `LEFT JOIN` 排除。

### SQL 设计参考
```sql
SELECT 
    cal.cal_date,
    basic.ts_code
FROM meta_trading_calendar cal
JOIN stock_basic_info basic 
    ON basic.list_date <= cal.cal_date 
    AND (basic.delist_date IS NULL OR basic.delist_date >= cal.cal_date)
LEFT JOIN stock_kline_daily kline
    ON kline.trade_date = cal.cal_date 
    AND kline.ts_code = basic.ts_code
WHERE cal.is_open = 1 
  AND kline.ts_code IS NULL;
```
*提示*: 配合索引 `idx_trade_date_ts_code` 可以实现秒级对账百万条记录。

---

## 2. 三段式自愈补数机制 (Triple-Source Recovery Flow)

针对三方金融数据 API 常出现的网络限流、单点数据丢失以及停牌不返回记录问题，应强制遵循以下三级自愈补数策略：

```
[疑似缺失代码] 
   │
   ├──► 1. Tushare 批量日线接口拉取 (覆盖率 95%+)
   │       └── 成功：写入 DB，标记 SUCCESS
   │
   └──► 2. Tushare suspend_d 停牌接口比对 (覆盖率 4%+)
           ├── 匹配：确认停牌，直接标记 SUCCESS 排除假空洞
           │
           └── 非停牌：触发 3. AkShare 单点回填补偿 (兜底 1%)
                   ├── 成功：写入 DB，标记 SUCCESS
                   └── 失败：标记 FAILED，防止占用队列死循环
```

### 核心收益
- **低 Token/积分开销**：Tushare 批量接口一次拉取全市场，仅对极少异常个股触发 AkShare 补偿，降级率控制在 1% 以下。
- **高鲁棒性**：AkShare（东方财富源/新浪源）的双重自动熔断切换，确保了弱网环境下的极端稳定性。

---

## 3. 影子随机对账采样算法

为了防范金融数据发生系统性字段偏离（如开高低收价格被错误除权），系统盘后应自动执行 **1% 影子随机对账**：
- **随机抽样**：从数据库当日入库数据中按 `ORDER BY RAND() LIMIT N` 抽样 1%。
- **对账规则**：对比影子源的开、高、低、收四价。
- **浮点数容差**：浮点数比对必须设置精度屏障，严禁使用等号。
  ```python
  if abs(float(local_price) - float(shadow_price)) > 0.011:
      # 触发差异告警，不一致率大于 0.01 元则标记异常
  ```
