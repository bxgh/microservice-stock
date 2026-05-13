# Task List: E7-S1 基于死线的全量降级逻辑

## Phase 1: 基础设施与元数据锁定 (T1)
- [x] **[E7-S1-T1.1]** `StockDAO`: 增加 `save_suspensions` 与 `ods_suspend_d` 存储能力。
- [x] **[E7-S1-T1.2]** `StockDAO`: 增加 `save_universe_snapshot` 与 `get_active_stock_codes` 逻辑。
- [x] **[E7-S1-T1.3]** `meta_sync`: 补齐 `sync_suspension` 操作，实现停牌数据二次元同步。
- [x] **[E7-S1-T1.4]** `meta_sync`: 实现 `create_universe_snapshot` 逻辑，锁定 09:30 采样基准。
- [x] **[E7-S1-T1.5]** 验证：通过 SQL 物理查验 `meta_universe_snapshot` 记录是否包含停牌对冲后的正确 $N$ 值。

## Phase 2: 完整性校验与 Fail-over 机制 (T2-T4)
- [ ] **[E7-S1-T2.1]** `daily_quotes`: 重构 17:00 任务入口，增加基准加载逻辑。
- [x] **[E7-S1-T2.2]** `daily_quotes`: 集成 `EmailNotifier` 发送 HTML 格式任务报告。
- [ ] **[E7-S1-T3.1]** `IntegrityValidator`: 实现基于快照的完整性审计模型 ($R_{final}$)。
- [ ] **[E7-S1-T4.1]** `AkShareAdapter`: 编写批量行情映射逻辑，对齐 `KLineModel` 契约。
- [ ] **[E7-S1-T4.2]** Fail-over 编排：实现 Tushare 失效时的自动回滚与 AkShare 补全链路。

## Phase 3: 影子审计与验收 (T5)
- [ ] **[E7-S1-T5.1]** 影子审计：实现常态化采集下的双源精度对比日志存证。
- [ ] **[E7-S1-T5.2]** 自动化验收：编写 Pytest 模拟 90% 采集率场景，验证是否成功触发切换。
- [ ] **[E7-S1-T5.3]** 交付文档：更新 `walkthrough.md` 嵌入物理证据。
