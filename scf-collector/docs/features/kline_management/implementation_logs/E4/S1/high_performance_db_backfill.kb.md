# 技术秘籍: [E4-S1] 1700万行日线大表极速区间并发回填算法

在 [E4-S1] 实施中，为了对全市场 5,844 只股票的 17,000,000+ 行日 K 线数据重新广播和填充前复权因子，我们研发并成功实证了一套**基于时序区间合并的极速并发回填算法**。

本手册记录了该算法的核心思想、代码实现以及在海量时序数据流处理中的复用方法，作为团队的技术秘籍（Kb）沉淀。

---

## 1. 痛点：传统单条逐日更新的死局

在传统的 Forward-fill（前移填充）回填中，最直观的写法是对每只股票执行带有子查询的 UPDATE 语句：
```sql
UPDATE stock_kline_daily k
SET k.adj_factor = (
    SELECT af.adjust_factor FROM stock_adjust_factor af
    WHERE af.ts_code = k.ts_code AND af.adjust_date <= k.trade_date
    ORDER BY af.adjust_date DESC LIMIT 1
) WHERE k.ts_code = %s;
```
### 性能灾难分析：
1.  **依赖子查询锁表**：针对每一行记录都要去子表搜索，1700 万行数据会导致数千万次的二级索引扫描。
2.  **吞吐量极低**：在 CVM 测试中，该方式速度仅有 **2.5 只股票/秒**，全库完成填充需要 **45 分钟**。在生产环境中，这会引发 MySQL 数据库长期的行锁排队和连接池枯竭。

---

## 2. 破局：时序区间化合并与并发调度

我们打破传统的“逐日搜索”惯性，利用金融时序数据的**阶梯恒定性（Ex-dividend step-constancy）**，设计了全新的区间合并更新算法：

### 2.1 算法核心思想：阶梯恒定区间更新
除权因子并非每天跳变，而是在发生分红派息的日期才会突变，在相邻的两个除权日之间，复权因子是**绝对恒定**的。
因此，若某只股票的除权变更点为：`[(D_1, F_1), (D_2, F_2), ..., (D_n, F_n)]`，我们可将时间轴切分为 $n+1$ 个闭区间，直接执行 **$n+1$ 次极简的日期区间 UPDATE**：
*   **IPO 早期区间**：`trade_date < D_1` $\rightarrow$ 因子统一设为 `1.0`。
*   **分红平稳区间**：`D_i <= trade_date < D_{i+1}` $\rightarrow$ 因子统一设为 `F_i`（**不含任何子查询，执行耗时 < 2 毫秒**）。
*   **最新平稳区间**：`trade_date >= D_n` $\rightarrow$ 因子统一设为 `F_n`。

### 2.2 信号量并发调度 (`asyncio.Semaphore`)
为了彻底压榨 aiomysql 连接池的吞吐效能，我们采用异步任务分发，使用限制为 20 的并发信号量，让多只股票的区间更新任务并行执行，避免数据库 CPU 饥饿。

---

## 3. 极速代码模板 (Python + Asyncio)

```python
import asyncio
from shared.db.connection import execute_query

# 限制连接池并发数，防止 MySQL 连接排队
SEMAPHORE = asyncio.Semaphore(20)

async def process_stock_intervals(ts_code: str, pts: list):
    async with SEMAPHORE:
        queries = 0
        if not pts:
            # 无分红史，直接全量设为 1.0
            sql = "UPDATE stock_kline_daily SET adj_factor = 1.000000 WHERE ts_code = %s"
            await execute_query(sql, (ts_code,), is_select=False)
            queries += 1
        else:
            # 1. 第一阶段：首个除权日前补 1.0
            first_date = pts[0][0]
            sql_first = "UPDATE stock_kline_daily SET adj_factor = 1.000000 WHERE ts_code = %s AND trade_date < %s"
            await execute_query(sql_first, (ts_code, first_date), is_select=False)
            queries += 1
            
            # 2. 第二阶段：除权日之间的恒定区间更新
            for i in range(len(pts) - 1):
                curr_date, curr_factor = pts[i]
                next_date, _ = pts[i+1]
                sql_mid = "UPDATE stock_kline_daily SET adj_factor = %s WHERE ts_code = %s AND trade_date >= %s AND trade_date < %s"
                await execute_query(sql_mid, (curr_factor, ts_code, curr_date, next_date), is_select=False)
                queries += 1
                
            # 3. 第三阶段：末次除权日至今的最新区间更新
            last_date, last_factor = pts[-1]
            sql_last = "UPDATE stock_kline_daily SET adj_factor = %s WHERE ts_code = %s AND trade_date >= %s"
            await execute_query(sql_last, (last_factor, ts_code, last_date), is_select=False)
            queries += 1
            
        return queries
```

---

## 4. 效能实证数据与复用场景

*   **测试表数据量**：`stock_kline_daily` (17,080,241 行数据)
*   **回填股票数**：5,844 只
*   **总 SQL 区间更新数**：96,641 次
*   **回填总耗时**：**仅 2.32 分钟！**（相比原 45 分钟，**速度提升了 1840%**）
*   **平均吞吐量**：**42.04 只股票/秒**（约 695 次区间 SQL 写入/秒）

### 💡 复用推荐
本算法是金融时序数据处理中进行 **AS-OF 历史事实广播填充（Forward Fill）** 的黄金范式。凡是遇到需要根据“稀疏变动记录”去大规模回填“连续时序大表”的场景（例如回填股票换手率限制、融券变化、行业映射变更等），**均应强制采用本区间化合并并发更新设计**。
