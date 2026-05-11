# Tasks for E200-S4: 白名单与 SLA 监控 (Governance)

- [x] **Phase 1: DB Schema Migration**
    - [x] [NEW] `migrations/20260511_create_meta_repair_whitelist.sql`
    - [ ] 执行数据库迁移并验证表结构

- [ ] **Phase 2: Governance Service Implementation**
    - [ ] [NEW] `stock-manager-api/app/services/governance_service.py`
    - [ ] 实现白名单自动过期逻辑 (`cleanup_expired_whitelist`)
    - [ ] 实现 SLA 自动化审计报告逻辑 (`generate_daily_sla_report`)

- [ ] **Phase 3: API & Ops Integration**
    - [ ] [MODIFY] `stock-manager-api/app/services/ops_service.py` (集成 SLA 报告)
    - [ ] [NEW] `stock-manager-api/app/api/governance.py` (暴露治理接口)
    - [ ] [MODIFY] `stock-manager-api/app/main.py` (挂载治理路由)

- [ ] **Phase 4: Verification & QC**
    - [ ] 编写单元测试验证白名单过期机制
    - [ ] 验证 SLA 报告统计准确性
    - [ ] 产出 `REPORT.md` 与 `walkthrough.md`
