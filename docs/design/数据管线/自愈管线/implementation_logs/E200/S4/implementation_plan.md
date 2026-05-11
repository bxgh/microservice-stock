# [E200-S4] 白名单与 SLA 监控 (Governance)

## 核心逻辑描述
本 Story 旨在建立数据管线的“长效治理”机制。通过引入白名单生命周期管理和 SLA 自动化审计，确保自愈系统在无人值守下的稳健运行，并量化评估数据质量治理的效果。
1. **白名单治理**: 实现自动过期机制（默认 5 交易日），防止“过期忽略”导致的数据质量黑洞。
2. **SLA 监控**: 统计自愈成功率与人工干预率，确保人工干预率控制在 ≤ 0.5% 的业务目标内。

## 角色激活
- [Data Quality Steward]: 负责治理规则与 SLA 审计指标定义。
- [Backend Developer]: 负责自动化清理任务与报表逻辑实现。

## User Review Required
> [!IMPORTANT]
> 默认白名单过期时间设为 **5 个交易日**。过期后记录将执行逻辑删除 (`is_deleted = 1`)。
> SLA 报告将集成至 `OpsService`，作为每日运维看板的一部分。

## Proposed Changes

### 1. 数据库变更 (DDL)
#### [NEW] [20260511_create_meta_repair_whitelist.sql](file:///home/ubuntu/microservice-stock/migrations/20260511_create_meta_repair_whitelist.sql)
- 建立 `meta_repair_whitelist` 表。
- 字段：`ts_code`, `trade_date`, `rule_id`, `reason`, `expire_at`, `created_at`, `updated_at`, `is_deleted`.

---

### 2. 核心服务 (Services)
#### [NEW] [governance_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/governance_service.py)
- **Whitelist Management**:
  - `add_to_whitelist(ts_code, trade_date, rule_id, reason, days=5)`: 添加记录，计算 `expire_at`。
  - `cleanup_expired_whitelist()`: 每日扫描并下线已过期的记录。
- **SLA Audit**:
  - `generate_daily_sla_report(date)`: 
    - 统计当日 `dq_findings` 总数、`RESOLVED` (自动修复) 数、`PENDING` (待人工) 数。
    - 计算 `Self-Heal Success Rate` 和 `Manual Intervention Rate`。

#### [MODIFY] [ops_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/ops_service.py)
- 增加 `get_sla_report()` 方法，调用 `GovernanceService` 并返回前端友好的 JSON。

---

### 3. API 接口 (Routes)
#### [NEW] [governance.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/api/governance.py)
- `POST /api/v1/governance/whitelist`: 手动添加白名单。
- `GET /api/v1/governance/sla_report`: 获取 SLA 审计报告。

---

## 验证计划

### 自动化测试
1. **过期逻辑验证**:
   - 插入一条 `expire_at` 为昨天的记录。
   - 调用 `cleanup_expired_whitelist()`。
   - 验证该记录的 `is_deleted` 变为 1。
2. **SLA 指标验证**:
   - 模拟 10 条 `dq_findings`，其中 9 条已修复，1 条仍为 OPEN。
   - 验证 SLA 报告显示的自动修复率为 90%。

### 手动验证
- 通过 `Mission Control` 页面（如果已有）或直接请求 API 观察 SLA 报告输出。
