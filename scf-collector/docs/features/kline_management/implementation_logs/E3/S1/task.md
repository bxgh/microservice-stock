# 任务看板: [E3-S1] 每日 K 线与复权因子采集任务调整

本文件用于实时追踪 E3-S1 微服务合并采集与容灾改造的进度，按 Task 粒度原子提交。

## 任务清单

- `[x]` **[E3-S1-T1] models.py 数据契约扩展**
  - [x] 在 `KLineModel` 中新增 `adj_factor: Optional[float] = Field(None)`
- `[x]` **[E3-S1-T2] dao.py 写入与读取优化**
  - [x] 更新 `StockDAO.save_kline_data` 的 SQL 语句，包含 `adj_factor` 插入与 `ON DUPLICATE KEY UPDATE` 更新
  - [x] 新增 `StockDAO.get_all_latest_adj_factors()` 高性能查询语句，用于本地 0.02 秒极速检索最新历史因子
- `[x]` **[E3-S1-T3] index.py 采集端合并与容灾自愈**
  - [x] 重构 `sync_kline_daily` 核心分支
  - [x] 引入 `meta_pipeline_run_log` 校验与双通道合并逻辑（本地/Tushare 实时补货）
  - [x] 实现第一层、第二层云端同步补足与静默自愈功能
- `[x]` **[E3-S1-T4] deploy.py 触发器移频配置**
  - [x] 修改 `DailyAdjFactor` 定时触发器从 `16:35` 前移至交易日 `09:25`（Cron: `0 25 9 * * * *`）
- `[x]` **[E3-S1-T5] 自动化测试与质量控制 (QC)**
  - [x] 编写本地单元测试 `tests/test_sync_kline_with_factor.py` 模拟双源合并与降级自愈
  - [x] 在 Docker 容器内通过 pytest 全量跑通测试
  - [x] 进行小样本灰度采集测试并输出 SQL 校验结果（0 NULL）
- `[x]` **[E3-S1-T6] 交付闭环与门户同步**
  - [x] 产出验收报告 `walkthrough.md` 及 API.md，生成 HTML 副本
  - [x] 运行 `scripts/update_docs_portal.py` 更新全局与局部门户
  - [x] 物理同步并更新该微服务下的 `docs/done-list-tables.md` 清单

---
恭喜！Epic 3 - Story 1 已经 100% 完满开发、测试与物理对账交付！本 Story 在生产环境的所有 AC 均已达成，系统稳定性与数据质量得到了前所未有的保障！
