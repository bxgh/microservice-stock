# Epic E12 K线质量保障踩坑与排障决策记录

> [!WARNING]
> 本文档记录了在构建 E12 数据质量巡检及自动修复引擎时遇到的诡异 Bug、性能瓶颈、网络/权限受阻等踩坑记录及择优决策。

---

## 1. 停牌股引发的“虚无空洞”警报

### 踩坑记录 (The Pitfall)
在执行 S1 完工审计时，系统报出大量历史“空洞”（特别是 2025-2026 年间）。经深入个股（如 `600671.SH` @ `2025-05-19`）单点排查，发现其在 Tushare 的 `daily` 接口中完全没有返回记录。由于审计脚本仅基于上市日期和交易日历进行强校验，便判定为“缺失”。

### 方案对比 (Options Explored)
- **方案 A**: 无视 Tushare 返回，强行从其它备选源拉取。
  - *缺点*: 极其浪费 API 额度，且其它源也可能因为停牌而无成交记录，导致无效重试。
- **方案 B**: 在对账时，前置引入 Tushare `suspend_d` 停牌接口进行交叉验证。
  - *优点*: 区分“真缺失”与“假空洞”（因停牌无数据）。

### 择优决策 (Optimal Choice)
采用 **方案 B**。更新 `auto_repair_worker.py` 行程逻辑，在补数前先加载当日停牌列表。如果某只股票在疑似缺失日确实处于停牌状态，引擎会将其视为“已解决（Resolved）”并将任务状态更新为 `SUCCESS`，从而避免重复尝试。

### 复用技巧 (Reusable Tips)
```python
# 停牌判定排除假空洞
suspensions = await self.collector.fetch_suspensions(trade_date)
suspended_codes = set([s['ts_code'] for s in suspensions]) if suspensions else set()
resolved_codes = fetched_codes.union(suspended_codes)
```

---

## 2. 影子源类名大小写拼写不一致 (Typo Blocking)

### 踩坑记录 (The Pitfall)
在集成 AkShare 作为 P2 影子补偿源时，发生了 `cannot import name 'AkshareCollector' from 'shared.collectors.akshare_cl'` 异常。原来是 `AkShareCollector` 的 `S` 字母大小写拼写不一致（脚本中写成了 `AkshareCollector`），导致顽固空洞修复崩溃并阻塞任务队列。

### 方案对比 (Options Explored)
- **方案 A**: 在报错时捕获异常并跳过。
  - *缺点*: 掩盖了类导入错误，导致以后此补偿路径永远无法走通。
- **方案 B**: 修复拼写，并针对外部包引入设置严格的异常捕获与日志记录。

### 择优决策 (Optimal Choice)
选择 **方案 B**。将拼写修正为 `AkShareCollector`，并在外部资源依赖导入时加入本地兜底。

---

## 3. 全网缺失股引发的“无限 Pending 死循环”

### 踩坑记录 (The Pitfall)
在处理最顽固的 18 只股票数据时，即使通过了 Tushare 批量、单点、停牌对账、AkShare 东方财富与新浪双源的五重检验，依然无法补齐。由于早期逻辑中，如果 AkShare 补不到数就不更新数据库状态，导致这 18 条记录永远处于 `PENDING`，被引擎无限循环扫描，造成资源浪费。

### 方案对比 (Options Explored)
- **方案 A**: 手动删除这些任务。
  - *缺点*: 下次重新跑审计脚本时，这些空洞还会被再次扫出来，治标不治本。
- **方案 B**: 增加 `FAILED` 终结状态。经过五重验证依然缺失的数据，强制标记为 `FAILED`，退出待修复队列。

### 择优决策 (Optimal Choice)
选择 **方案 B**。对 `auto_repair_worker.py` 进行逻辑微调，增加 `FAILED` 状态作为兜底，防止死循环。

---

## 4. aiomysql 异步连接池 `Event loop is closed` 异常

### 踩坑记录 (The Pitfall)
在脚本顺利退出时，控制台频繁抛出 `RuntimeError: Event loop is closed`。这是由于 `aiomysql` 的 `Connection.__del__` 在异步垃圾回收时，事件循环已经关闭，导致资源未优雅释放。

### 择优决策 (Optimal Choice)
在脚本生命周期结束前，显式调用 `await DBManager.close_all()` 关闭底层连接池，并在 `finally` 块中确保连接和 pool 均已安全 `close` 和 `wait_closed`。
