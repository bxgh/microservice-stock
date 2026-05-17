# 实施方案: [E4-S1] 跨源前复权价格一致性校验 (100只股票全量历史审计)

在 Epic 3 成功将 `adj_factor` 内嵌写入 `stock_kline_daily` 且达到 100% 覆盖后，我们必须对**内嵌因子动态前复权公式的正确性**进行严苛的跨源对账校验。
本方案针对用户提出的“**对 100 只股票的所有历史数据进行前复权一致性校验**”要求，设计了一套高能效、不超频的批量比对机制。

---

## User Review Required

### 100只股票全量历史高能效对账策略

1. **执行物理环境约束**：
   > [!IMPORTANT]
   > 本次对账校验将**完全运行在云服务器 (CVM) 环境下**（在本地拉取数据并与 Tushare 对账，输出 CSV 文件于云服务器上），**绝对不在 SCF 无服务器云函数端执行**，以避免不必要的云函数资源消耗和网络延迟，并保证文件落盘的可复核性。

2. **校验覆盖深度**：相比设计文档中仅随机抽样 500 个点，本项目实施将直接挑战**100只核心股票的所有历史交易日（约250,000个对账点）**的完整覆盖比对。
3. **Tushare 接口防超频设计**：
   - 严禁逐日或逐股零散发起 API 请求（极易触发流量控制且消耗大量点数）。
   - **优化策略**：对 100 只精选股票（优先选取沪深 300 蓝筹股及历史除权除息频繁的代表性股票），采用**股票级批量抓取**：
     - 使用 `pro.daily(ts_code=...)` 批量抓取单只股票全部历史行情。
     - 使用 `pro.adj_factor(ts_code=...)` 批量抓取单只股票全部历史因子。
   - 这种股票级批量抓取仅需 **200 次 API 调用**，可在 **30 秒内**完成全部数据拉取，既能完成 25 万个对账点的地毯式校验，又不会触发 any 限流。
4. **计算公式与容差判定**：
   - **本地前复权收盘价**：$LocalQFQ = Close_{local} \times \frac{AdjFactor_{local}}{LatestFactor_{local}}$
   - **官方基准前复权收盘价**：$RefQFQ = Close_{tushare} \times \frac{AdjFactor_{tushare}}{LatestFactor_{tushare}}$
   - **容差标准 (AC)**：相对误差 $\frac{|LocalQFQ - RefQFQ|}{RefQFQ} \le 10^{-3}$（即 $0.1\%$）。若出现误差超标的点，自动将其输出至 `qfq_anomalies.csv` 供人工复核。

---

## Proposed Changes

### 数据校验与对账层 (`scf-collector/scratch`)

#### [NEW] [verify_100_stocks_qfq.py](file:///home/ubuntu/microservice-stock/scf-collector/scratch/verify_100_stocks_qfq.py)
- **核心逻辑**：
  1. 从本地数据库选取 100 只交易活跃、历史数据饱满的代表性股票（涵盖上证、深证主板、创业板）。
  2. 针对每只股票，批量拉取本地 `stock_kline_daily` 行情与内嵌 `adj_factor`。
  3. 通过 Tushare 批量拉取官方行情与官方因子，在内存中按日期进行对齐并计算基准前复权价格。
  4. 逐日对齐比对，统计相对误差。
  5. 将所有误差超标的异常记录以及详细比对参数（ts_code, trade_date, local_qfq, ref_qfq, error）输出至 `qfq_anomalies.csv`。
  6. 统计总异常率是否满足 **AC1（异常率 < 0.2%）** 标准。

---

## Verification Plan

### Automated Tests
1. **运行物理校验脚本**：
   - 在 `.venv` 环境下在云服务器执行：
     ```bash
     .venv/bin/python scf-collector/scratch/verify_100_stocks_qfq.py
     ```
   - 检查控制台输出的异常率及明细，确保异常点占比满足 AC1。

### Manual Verification
1. **异常复核 (Anomalies Review)**：
   - 检查是否生成了 `qfq_anomalies.csv` 文件。
