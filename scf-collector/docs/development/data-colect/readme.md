# 数据采集实施指南 (Data Collection Implementation)

本目录记录 `scf-collector` 模块中各数据分类的实施细节。

## 核心设计
- **设计标准**: [E400_SCF_Collector_Implementation.md](file:///home/ubuntu/microservice-stock/scf-collector/docs/E400_SCF_Collector_Implementation.md)
- **优先级**: P0 核心行情 -> P1 日线指标 -> P2 基本面 -> P3 资金与事件
- **任务看板**: [todo-list-tables.md](file:///home/ubuntu/microservice-stock/scf-collector/docs/todo-list-tables.md)

## 1. 开发前准入 (Admission)

> [!CAUTION]
> **强力审计**: 在开始任何 Story 开发前，**必须执行以下物理查验**，严禁仅凭文档进行开发。

1. **物理表查验**: 通过 SQL 执行 `DESC <table_name>` 确认物理字段与 `TABLES_INDEX.md` 的实际差异。
2. **存量数据量纲抽检**: 检查存量数据的单位（如成交额是元还是万元）及 `pct_chg` 的存储格式（小数还是百分比）。
3. **E300 报告对齐**: 必须阅读 **[E300-S1 审计报告](file:///home/ubuntu/microservice-stock/docs/design/数据管线/implementation_logs/E300/S1/REPORT.md)**，明确已知的字段缺失或命名冲突。

## 2. 设计目标 (Design Goals)

- **高可靠抓取**: 实现 3 次指数退避重试，处理 Tushare 积分限流与网络抖动。
- **内存极限控制**: 严格限制单实例内存 ≤ 256MB，海量数据（如 K 线、财报）必须使用 `chunksize` 流式读写。
- **数据规格标准性**: 物理落库字段 100% 对齐 `TABLES_INDEX.md` 定义，通过采集层 Mapping 规避「命名差异」与「量纲陷阱」。
- **存量数据先行核对**: 开发前必须核对 MySQL 数据库的物理表结构与存量数据（参考 E300 审计报告），遵循「存量兼容、增量标准」原则，严禁盲目新建同类表。
- **事件驱动编排**: 采集完成后必须触发 `meta_data_readiness` 信号，确保下游流水线接力。

## 2. 实施阶段 (Stages)

1. [ ] **E400-S1: 核心行情与因子**: 包含不复权 K 线、复权因子、申万行业成员（P0 级优先级）。
2. [ ] **E400-S2: 日线指标与异动**: 包含每日估值、停复牌、基金净值及同花顺概念。
3. [ ] **E400-S3: 财务与股东数据**: 处理三大会计报表及十大股东，关注季度同步吞吐量。
4. [ ] **E400-S4: 资金流与公告事件**: 包含主力资金、北向持仓、龙虎榜及重大公告。

## 3. 验收标准 (Acceptance Criteria)

- **AC1: 数据契约对齐性**: 
    - [ ] 物理表结构与 `TABLES_INDEX.md` 100% 对应，采集层已处理 `vol`->`volume` 等映射。
    - [ ] 关键字段（如 `amount`, `pct_chg`）量纲转换逻辑已通过代码审计。
- **AC2: 任务幂等性**: 
    - [ ] 同一业务日期重复运行，数据库无重复记录，且 `updated_at` 正常更新。
- **AC3: 采集时效性**: 
    - [ ] P0 级数据同步必须在交易日 16:00 前完成并标记 `READY`。
- **AC4: 资源稳定性**: 
    - [ ] SCF 监控日志中未出现 `Memory Limit Exceeded` 或 `Task Timeout`。

## 4. 关键约束 (Constraints)

- **内存限制**: 单函数实例 ≤ 256MB。
- **并发控制**: 遵守 Tushare 积分限流。
- **数据对齐**: 严格执行 `AGENTS.md` 命名与量纲规范。
