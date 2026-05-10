# 技术报告 - E200-S2: 自动化修复与回滚引擎 (Healer)

## 1. 核心目标
自动化修复与回滚引擎（Healer）是自愈型数据管线的核心执行组件。其职责是闭环 E200-S1 (Scanner) 发现的数据质量异常，通过多源仲裁建议自动回填正确数据，并建立原子级的回滚机制，确保数据修复过程的安全性和可逆性。

## 2. 修复工作流 (Healer Workflow)

系统采用“快照先行，原子更新”的执行策略，具体流程如下：

### 2.1 触发与扫描
- **准入条件**: 仅处理 `dq_findings` 表中 `status = 'OPEN'` 且 `severity` 为 `ERROR` 或 `CRITICAL` 的记录。
- **仲裁提取**: 解析 `diff_data` 中的 `consensus_source` 字段，确定最优回填源。

### 2.2 快照存证 (Snapshotting)
在执行任何数据库更新前，Healer 会对目标行执行全字段扫描：
- **存储位置**: `meta_repair_log.before_snapshot` (JSON 格式)。
- **作用**: 提供原始“作案现场”的镜像，作为一键回滚的基准。

### 2.3 数据补偿与回填 (Backfill)
- **多源适配**: 支持 `MOOTDX` (直连行情)、`TUSHARE` 及 `AKSHARE`。
- **幂等更新**: 采用 `UPDATE` 覆盖模式。针对 A 股 legacy 表（如 `stock_kline_daily`）缺乏 `updated_at` 的现状，执行层自动适配 SQL 语句，确保兼容性。

### 2.4 级联失效 (Cascade Invalidation)
修复完成后，Healer 自动触发级联清理信号：
- 调用 `backfill_service.invalidate_downstream`。
- 根据数据血缘清理所有受影响的 ADS 层视图及派生指标，防止“脏数据”在下游链路扩散。

## 3. 回滚机制 (Rollback Logic)

为应对修复误判或源数据二次污染，Healer 提供了原子级回滚能力：
- **逻辑**: 读取 `meta_repair_log` 中的 `before_snapshot`，将字段状态原样覆盖回目标表。
- **状态迁移**: 成功回滚后，修复日志状态标记为 `ROLLED_BACK`。

## 4. 技术健壮性设计
- **Decimal 序列化**: 针对 MySQL `Decimal` 类型与 Python JSON 序列化的冲突，增加了递归清洗函数 `_sanitize_snapshot`。
- **异步处理**: 修复任务支持 `BackgroundTasks` 异步执行，避免阻塞 API 响应。
- **审计闭环**: 所有修复行为（含成功/失败）均持久化至 `meta_repair_log`。

---
*本报告作为 E200-S2 实施任务的正式交付文档。*
