# [E200-S2] 自动化修复与回滚引擎 (Healer)

## 核心逻辑描述
本 Story 旨在实现自愈管线的“执行”环节。当 E200-S1 (Scanner) 发现 ODS 数据异常并判定出仲裁建议后，本引擎将自动触发修复流程：抓取正确源数据、备份旧数据镜像、更新目标表，并提供一键回滚能力以应对修复误判。

## 角色激活
- [Backend Developer]: 负责 FastAPI 接口与服务逻辑实现。
- [Data Quality Steward]: 负责审计表设计与数据完整性保障。

## User Review Required
> [!IMPORTANT]
> `meta_repair_log` 将作为新的系统审计表，专门记录“自愈性修复”操作。原有的 `backfill_audit` 保持兼容，但高阶自愈逻辑将优先使用 `meta_` 系列表。

## Proposed Changes

### 1. 数据库变更 (DDL)
#### [NEW] [20260510_create_meta_repair_log.sql](file:///home/ubuntu/microservice-stock/migrations/20260510_create_meta_repair_log.sql)
- 建立 `meta_repair_log` 表。
- 包含 `finding_id` (关联异常项), `snapshot_before`, `snapshot_after`, `status` 等核心字段。

### 2. 模型定义 (Schemas)
#### [NEW] [meta.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/models/meta.py)
- 定义 `RepairLog` 相关的 Pydantic 模型。

### 3. 核心服务 (Services)
#### [NEW] [healer_service.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/services/healer_service.py)
- **BackfillCoordinator**: 
  - `scan_and_repair()`: 定时或手动触发的任务，处理 `dq_findings` 中的 `OPEN` & `ERROR` 记录。
  - `execute_repair(finding_id)`: 原子修复单元。
    - 1. 提取仲裁结果（建议使用的源）。
    - 2. 备份当前 ODS 镜像。
    - 3. 调用 `Mootdx` / `Tushare` 获取正确数据。
    - 4. 更新 ODS 并记录 `meta_repair_log`。
    - 5. 标记 `dq_findings` 为 `RESOLVED`。

### 4. API 接口 (Routes)
#### [NEW] [healer.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/api/healer.py)
- `POST /api/v1/healer/repair`: 启动扫描修复。
- `POST /api/v1/healer/rollback/{repair_id}`: 执行回滚，恢复 `snapshot_before` 数据。

#### [MODIFY] [main.py](file:///home/ubuntu/microservice-stock/stock-manager-api/app/main.py)
- 挂载 healer 路由。

---

## Verification Plan

### Automated Tests
1. **修复流程验证**:
   - 向 `dq_findings` 注入一条模拟异常记录（建议由 Mootdx 修复）。
   - 调用 `/healer/repair` 接口。
   - 验证 ODS 表对应数据已被更新。
   - 验证 `meta_repair_log` 产生 `SUCCESS` 记录。
2. **回滚流程验证**:
   - 调用 `/healer/rollback/{id}`。
   - 验证 ODS 数据恢复至 `snapshot_before`。
   - 验证 `meta_repair_log` 状态更新为 `ROLLED_BACK`。

### Manual Verification
- 通过 SQL 查询 `meta_repair_log` 确认 JSON 格式的快照准确性。
