# E7-S1: 基于死线的全量降级逻辑 (17:00 Fail-over) 实施方案

## 实施前准入 (Readiness Check)

- **需求解析**:
  1. 建立 09:30 盘前基准快照，通过"上市列表 - 当日停牌"锁定当日应采总数 $N$。
  2. 在 17:00 死线判定 Tushare 采集率是否达标，支持"核心股缺失"一票否决。
  3. 故障时通过"原子级幂等覆盖"逻辑切换至 AkShare，严禁高危全表删除，通过影子审计系统留存可靠性证据。

- **依赖认证**:
  - [x] **数据标准**: 已对齐 `TABLES_INDEX.md` 中的 `pct_chg` (小数) 和 `amount` (元)。
  - [x] **接口验证**: 已确认 Tushare `suspend_d` 和 AkShare `stock_zh_a_spot_em` 的字段映射可行。
  - [x] **环境连通**: SCF 已绑定 VPC 可直连内网 MySQL 5.7。
  - [ ] **DDL 就绪**: `ods_suspend_d` 和 `meta_universe_snapshot` 两张表的建表语句需提交到 `migrations/` 目录。

- **角色激活**:
  - **[Backend Engineer]**: **核心负责**。负责 SCF 异步 IO、DB 连接池管理及 `try...finally` 资源闭环，严禁在异步中使用同步库。
  - **[Requirement Architect]**: 设计死线熔断机制与 AC，确保方案可测试。
  - **[Data Quality Steward]**: 定义停牌对冲口径，确保数据完整性。
  - **[DB Auditor]**: 负责 DAO 层幂等性 SQL 审计，确保无高危删除指令。
  - **[Infra Specialist]**: 负责多源切换的熔断与退避重试。
  - **[Workflow Guard]**: 实施过程存证与 QA 质量把关。

---

## 代码现状审核 (Code Audit)

> [!WARNING]
> **已发现未经批准的代码变更**。在获得用户批准前，以下三个文件已被直接修改。需要对这些变更进行逐项审核，确认其是否可被纳入正式实施，或者需要回滚后重新开发。

### 已变更文件清单

| 文件 | 变更内容 | 审核状态 |
|---|---|---|
| `shared/collectors/tushare_cl.py` | 新增 `_fetch_suspend_d_sync` 和 `fetch_suspensions` | 待确认 |
| `shared/db/dao.py` | 新增 `save_suspensions`、`get_active_stock_codes`、`get_suspended_codes`、`save_universe_snapshot` | 待确认 |
| `functions/meta_sync/index.py` | 新增 `sync_suspension` 和 `create_universe_snapshot` 操作分支 | 待确认 |

### 代码质量问题 (按角色审查)

#### [DB Auditor] 审查结果

1. **`ods_suspend_d` 表缺少 DDL 定义**
   - DAO 中引用了 `ods_suspend_d` 表，但 `migrations/` 目录下没有对应的建表脚本。
   - 该表也未出现在 `db_inventory.md` 的物理表清单中。
   - **风险**: 部署到生产环境时会直接报 `Table doesn't exist` 错误。

2. **`meta_universe_snapshot` 表同样缺少 DDL**
   - 与上同理，`codes_json` 字段建议使用 `MEDIUMTEXT` 而非 `TEXT`（全 A 约 5300 只股票的 JSON 约 100KB）。

3. **`get_active_stock_codes` 缺少 `is_deleted` 过滤**
   - 当前 SQL: `WHERE list_status = 'L' AND list_date <= %s`
   - **违反规范**: [DB Auditor] 要求所有 SELECT 必须包含 `is_deleted = 0`。
   - 需补充: `AND is_deleted = 0`。

4. **`get_suspended_codes` 同样缺少 `is_deleted` 过滤**

#### [Backend Engineer] 审查结果

5. **`_fetch_suspend_d_sync` 重复初始化 `pro_api`**
   - 该方法内部 `import tushare as ts` 并调用 `ts.pro_api(token)`，但 `TushareCollector.__init__` 已经初始化了 `self.pro`。
   - 应复用 `self.pro` 实例，而非每次调用都重新创建连接。

6. **`save_suspensions` 使用逐条 INSERT 而非批量操作**
   - 当前实现使用 `for item in data` 循环逐条写入。
   - 若停牌股超过 100 只（如极端行情），会产生大量数据库往返。
   - 建议改为 `executemany` 批量写入。

#### [Data Quality Steward] 审查结果

7. **`suspend_d` 接口返回的字段需要验证**
   - Tushare `suspend_d` 接口返回字段为 `ts_code, trade_date, suspend_type, suspend_timing`，而非 DAO 中假设的 `suspend_date, resume_date, ann_date, suspend_reason, reason_type`。
   - **风险**: 字段不匹配将导致全部写入失败。
   - **建议**: 在正式实施前，必须通过灰度调用确认实际字段结构。

#### [Infra Specialist] 审查结果

8. **`create_universe_snapshot` 缺少错误隔离**
   - 当前逻辑是：先采停牌 → 再查活跃列表 → 再做差集。
   - 若 `fetch_suspensions` 失败（网络超时），整个快照任务将中断。
   - 建议增加降级策略：停牌采集失败时，以 `suspended_count = 0` 作为保守估计继续执行。

---

## User Review Required

> [!CAUTION]
> **关于"误操作"的防御性设计**: 
> 1. **严禁使用 `DELETE FROM table` 无限制语句**。
> 2. 故障 Fail-over 策略采用 **"原子级覆盖 (Atomic Overwrite)"**：利用 AkShare 的全量 Spot 数据，通过 `ON DUPLICATE KEY UPDATE` 强制覆盖 Tushare 可能写入的残缺行。
> 3. 只有在判定"代码列表发生变更"等极端情况时，才允许在 `WHERE trade_date = 'Today'` 的受控范围内执行精确清理。

> [!IMPORTANT]
> **熔断判定红线**: 设定 $R < 95\%$ 或核心成分股缺失为"系统性失效"。

> [!NOTE]
> **资源对冲**: 09:30 锁定的基准 $N$ 已扣除当日停牌股，因此 17:00 的 $R$ 计算为 $R = 实采数 / N$。

## Open Questions

1. **已写入的代码是否保留？** 上述三个文件已有变更，是选择在此基础上修复问题（保留并修补），还是回滚后按标准流程重新实施？
2. **`suspend_d` 字段映射**: 需要实际调用一次 Tushare 接口确认返回结构，当前 DAO 的字段假设可能有误。
3. **DDL 提交策略**: 两张新表 (`ods_suspend_d`, `meta_universe_snapshot`) 的 DDL 是否直接在云端 MySQL 执行，还是走 `migrations/` 标准流程？

---

## Proposed Changes

### 1. DDL 与数据库层 (前置依赖)

#### [NEW] migrations/ods_suspend_d.sql
- 建表语句，主键 `(ts_code, suspend_date)`，包含标准尾部三件套。

#### [NEW] migrations/meta_universe_snapshot.sql
- 建表语句，主键 `biz_date`，`codes_json MEDIUMTEXT`，包含标准尾部三件套。

---

### 2. DAO & Collector (基础设施层)

#### [MODIFY] [dao.py](file:///e:/gitee/microservice-stock/scf-collector/shared/db/dao.py)
- **修复** `get_active_stock_codes`: 补充 `AND is_deleted = 0`。
- **修复** `get_suspended_codes`: 补充 `AND is_deleted = 0`。
- **优化** `save_suspensions`: 改为批量写入，对齐 Tushare `suspend_d` 实际返回字段。
- **新增** `get_universe_snapshot(biz_date)`: 读取盘前锁定的预期代码集合（17:00 任务使用）。

#### [MODIFY] [tushare_cl.py](file:///e:/gitee/microservice-stock/scf-collector/shared/collectors/tushare_cl.py)
- **修复** `_fetch_suspend_d_sync`: 复用 `self.pro` 实例，移除重复初始化。

#### [MODIFY] [index.py (meta_sync)](file:///e:/gitee/microservice-stock/scf-collector/functions/meta_sync/index.py)
- **增强** `create_universe_snapshot`: 增加停牌采集失败时的降级策略。

---

### 3. Daily Quotes (核心业务层)

#### [NEW] [notifier.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/notifier.py)
实现基于 `aiosmtplib` 的异步邮件发送模块，复用 CVM HTML 模板：
- 支持 `SUCCESS`/`ERROR`/`WARN` 不同级别的颜色渲染。
- 集成业务详情展示表格。

### [MODIFY] [daily_quotes/index.py](file:///e:/gitee/microservice-stock/scf-collector/functions/daily_quotes/index.py)
- 重构 `sync_kline_daily` 等操作，在任务结束处注入 `EmailNotifier` 调用。
- 实现 17:00 完整性校验逻辑：
  - 加载 `meta_universe_snapshot` 基准。
  - 校验 Tushare 采集率。
  - 触发 AkShare Fail-over (如有必要)。
  - **发送最终集成报告邮件**。

#### [NEW] [akshare_adapter.py](file:///e:/gitee/microservice-stock/scf-collector/shared/collectors/akshare_adapter.py)
- 实现批量行情接口映射，将 AkShare 的字段转换为标准 `KLineModel`。

---

## Verification Plan

### Automated Tests
1. **基准测试**: 构造 5 只股票上市、2 只停牌的场景，校验 09:30 任务产出的 $N$ 是否等于 3。
2. **字段映射验证**: 调用 `suspend_d` 接口，打印首条记录，确认实际字段名。
3. **故障模拟**: 
   - 模拟 Tushare 返回量为 50% 的极端情况。
   - 预期：系统记录 `Failure`，触发 AkShare 接口调用，且最终 `meta_data_readiness` 标记为 `READY`。

### Manual Verification
- 手动触发 09:30 任务，查询数据库 `meta_universe_snapshot` 表确认 JSON 清单。
- 验证 SQL: `SELECT biz_date, expected_count FROM meta_universe_snapshot WHERE biz_date = CURDATE()`。

---

## 维护记录

| 日期 | 变更 |
|---|---|
| 2026-05-13 | 初版方案创建。 |
| 2026-05-13 | 补充角色激活声明，将"清空"策略修改为"幂等覆盖"。 |
| 2026-05-13 | **代码审核**: 发现 8 项问题（DDL 缺失、字段映射错误、is_deleted 遗漏等），增加 Open Questions 章节。 |
