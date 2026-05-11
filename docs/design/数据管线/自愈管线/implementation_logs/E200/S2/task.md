# Task List - E200-S2: 自动化修复与回滚引擎 (Healer)

- [x] **E200-S2-T1: 审计镜像存储建立 (DDL)**
    - [x] 创建迁移文件 `migrations/20260510_create_meta_repair_log.sql`
    - [x] 执行迁移并验证表结构
- [x] **E200-S2-T2: BackfillCoordinator 核心逻辑开发**
    - [x] 创建 `app/models/meta.py` 定义 Pydantic 模型
    - [x] 实现 `HealerService.execute_repair` 支持备份、抓取与更新
    - [x] 实现 `HealerService.scan_and_repair` 处理 `dq_findings`
- [x] **E200-S2-T3: 原子级回滚与 API 交付**
    - [x] 实现 `HealerService.rollback_repair`
    - [x] 创建 `app/api/healer.py` 路由
    - [x] 在 `main.py` 注册路由
- [x] **E200-S2-QC: 验收测试**
    - [x] 编写并执行自动化测试用例 (Given-When-Then)
    - [x] 验证回滚一致性
