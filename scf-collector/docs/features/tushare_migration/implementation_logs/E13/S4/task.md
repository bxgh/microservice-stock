# E13-S4: 财务三表与关键比率迁移 — 任务进度跟踪

本文件用于实时追踪 E13-S4 各个 Task 的执行进度。每个小项完成时将标记为 `[x]` 并关联具体的 Commit ID。

---

## 任务看板

- `[ ]` **E13-S4-T1**: 开发数据源组件 `TushareCollector` 的异步财务数据拉取逻辑
  - `[ ]` 在 `tushare_cl.py` 中使用 `asyncio.to_thread` 封装 `balancesheet` (资产负债表) 接口
  - `[ ]` 在 `tushare_cl.py` 中封装 `income` (利润表) 接口
  - `[ ]` 在 `tushare_cl.py` 中封装 `cashflow` (现金流量表) 接口
  - `[ ]` 在 `tushare_cl.py` 中封装 `fina_indicator` (财务指标) 接口
- `[ ]` **E13-S4-T2**: 开发数据库访问层 `StockDAO` 的高效率幂等插入方法与字段规范化
  - `[ ]` 在 `dao.py` 中实现 `save_balancesheet` 批量保存，进行字段别名对齐
  - `[ ]` 在 `dao.py` 中实现 `save_income` 批量保存
  - `[ ]` 在 `dao.py` 中实现 `save_cashflow` 批量保存
  - `[ ]` 在 `dao.py` 中实现 `save_fina_indicator` 并对百分比字段进行**除以 100.0** 的标准化换算
- `[ ]` **E13-S4-T3**: 开发核心回填跑批脚本 `tushare_financial_backfill.py`
  - `[ ]` 实现基于 `sync_progress` 的个股断点续传（task_name='financial_sheets_backfill'）
  - `[ ]` 实现单线程 1.5s 的 Throttling (休眠控流) 策略，保障 Tushare 与 MySQL 稳定性
  - `[ ]` 实现 Python 业务层的时序去重，按报告期仅保留最新的一条公告记录
  - `[ ]` 集成炫酷的可视化 CLI 进度条与性能估计
- `[ ]` **E13-S4-T4**: 编写并执行单元测试与物理数据 QC 审计
  - `[ ]` 编写并执行单元对账测试用例，覆盖字段映射、百分比换算与幂等防重
  - `[ ]` 物理连接数据库执行数据完整性 SQL 审计 (无未来函数、小数标准化及去重无冗余审计)
- `[ ]` **E13-S4-T5**: 产出交付物，编译发布文档与全局门户更新
  - `[ ]` 撰写 `REPORT.md`/`REPORT.html` 技术交付报告
  - `[ ]` 更新 AI-to-AI `state_E13.json` 状态交接文件，归纳已交付资产
  - `[ ]` 运行 `python scripts/update_docs_portal.py` 更新系统全局与局部 Portal 导航
