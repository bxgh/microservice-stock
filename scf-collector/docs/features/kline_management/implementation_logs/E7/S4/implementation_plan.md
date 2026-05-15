# E7-S4: 采集完整性校验与备份源接管 (Integrity & Fail-over) v2

## 0. 实施前准入 (Readiness Check)
- [x] **需求解析**: 16:30 主采集完成后，**17:00 触发校验任务**，以 09:30 基准快照为分母计算覆盖率；若不达标，允许 Tushare 原位重试一次；若重试后仍 < 95% 或丢失权重股，则启动 AkShare 全量接管。
- [x] **依赖认证**: `meta_universe_snapshot` 已有 09:30 数据（S1 已落地）；`ShadowAuditor` 已具备全量对账能力（S2 已落地）；`AkShareAdapter` 已通过 KLineModel 契约验证（S3 已落地）。
- [x] **角色激活**: `[Data Quality Steward]` (审计模型增强) + `[Backend Engineer]` (调度编排) + **`[QA/Test Engineer]` (负责故障注入测试)**。

## 1. 业务背景

经过重新评估，S2 的 `ShadowAuditor` 已经具备了 S4 所需的大部分能力（AkShare 拉取、适配转换、覆盖率比对、存证）。其核心缺陷仅有两点：

1. **基准错误**: `expected_count` 取的是主源实采数 `len(df_p)`，属于"自己和自己比"，无法发现大面积漏采。
2. **缺少执行能力**: 审计员只记录不行动，无法触发重试或备份源接管。

因此，S4 不再新建 `IntegrityValidator` 类，而是**增强现有组件 + 增加编排逻辑**。

## 2. User Review Required

> [!IMPORTANT]
> **设计变更**: 相比 v1 方案（新建 `IntegrityValidator`），v2 方案改动量大幅缩减。核心逻辑集中在 `ShadowAuditor` 增强和 `index.py` 编排两处，降低了引入新抽象的维护成本。

## 3. Open Questions

- **成分股探测**: 暂不实现沪深 300 成分股的"特权检查"。先以纯覆盖率阈值（95%/98%）做判定，后续按需迭代。

## 4. 拟议变更

### [Component] shared/utils

#### [MODIFY] [shadow_auditor.py](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/shadow_auditor.py)

**变更 1: 基准来源修正 (L114)**
```python
# 现状 (错误):
"expected_count": len(df_p),  # 自己和自己比

# 修改为:
snapshot = await StockDAO.get_universe_snapshot(trade_date)
baseline_n = snapshot['expected_count'] if snapshot else len(df_p)
"expected_count": baseline_n,
```

**变更 2: 覆盖率公式修正**
```python
# 现状: coverage = overlap / len(df_p)  (主源内部重叠率)
# 修改为: coverage = len(df_p) / baseline_n  (主源实采 vs 09:30 基准)
```

**变更 3: 返回值增强**
- 新增 `diff_list` 字段：基准代码集与实采代码集的差集（JSON）。
- 新增 `source_tag` 字段：标记最终采纳的数据源。

---

### [Component] shared/db

#### [MODIFY] [dao.py](file:///e:/gitee/microservice-stock/scf-collector/shared/db/dao.py)

- 新增 `get_universe_snapshot(biz_date)` 方法：读取 09:30 锁定的基准快照（`expected_count` + `codes_json`）。
- 增强 `save_audit_log`: 支持 `diff_list` (TEXT/JSON) 和 `source_tag` 字段写入。

---

### [Component] functions/daily_quotes

#### [MODIFY] [index.py](file:///e:/gitee/microservice-stock/scf-collector/functions/daily_quotes/index.py)

在现有 `sync_kline_daily` 逻辑之后，新增 `validate_and_failover` 操作分支（约 30 行）：

```
17:00 触发 op='validate_and_failover'
  ├── 1. 加载 09:30 基准快照 (expected_count)
  ├── 2. 查询 DB 中 16:30 实际入库数量
  ├── 3. 计算 coverage = actual / expected
  ├── 4. IF coverage >= 98%  → PASS, 更新就绪信号
  ├── 5. IF coverage < 98%   → 重试 Tushare 一次
  │       ├── 重试后达标 → PASS
  │       └── 重试后仍 < 95% → 触发 Fail-over
  └── 6. Fail-over: 调用 AkShareCollector.fetch_all_stock_spot()
          ├── 转换为 KLineModel
          ├── 覆盖入库
          └── 记录 source_tag = 'AKSHARE_P1_FAILOVER'
```

---

### [Component] migrations

#### [NEW] V1.4_E7_S4_Audit_Enhancement.sql
- `meta_data_audit_log` 增加 `diff_list` (TEXT) 和 `source_tag` (VARCHAR) 字段。

## 5. 验证计划

### Automated Tests
- 模拟 16:30 仅入库 4000 条（基准 5300），验证 17:00 校验是否触发重试。
- 模拟重试后仍不足 95%，验证是否调用 AkShare 全量补录。
- SQL 审计：验证 `meta_data_audit_log` 中 `diff_list` 和 `source_tag` 是否正确记录。

### Manual Verification
- 在 SCF 控制台手动触发 `validate_and_failover` 操作，观察日志链路。
