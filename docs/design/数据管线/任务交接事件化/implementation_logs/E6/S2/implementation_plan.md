# 实施计划 - E6-S2: 每日任务调度合理化分配 (Rationalizing Task Scheduling)

## 角色激活
- **[Infrastructure Architect]**: 负责三阶段流水线重构与事件探测机制设计。
- **[Reliability Engineer]**: 负责深夜任务错峰逻辑实现、数据库 Schema 补全及 Mission Control 监控开发。

## 需求解析
将原本分散、静态的 Cron 调度系统重构为“全生命周期三段式编排”架构。核心目标是消除空转、降低数据库峰值压力、并实现全天候运行看板。

## 依赖认证
- [x] `WorkflowService` 具备基础状态机能力。
- [x] `meta_pipeline_run` 表已就绪。
- [x] Tushare 接口积分充足（用于 Canary 探测）。

## 拟议变更

### Phase I: 晨间预就绪 (08:00 - 09:30)
- 探测 Tushare `suspend_d` 数据投放。
- 顺序执行：基础信息同步 -> 停牌/业绩预告 -> DQ 审计。

### Phase II: 盘后流水线 (15:00 - 23:00)
- 整合基金同步任务至 Stage A。
- 维持原有的 B/C/D 阶段事件驱动。

### Phase III: 深夜维护 (01:00 - 05:00)
- 财务数据、机构评级、股东数据同步。
- 实施 45 分钟错峰逻辑。

### 监控看板
- 开发 `GET /api/v1/ops/mission-control`。

## 验证计划 (QA)

### 自动化/脚本验证
- [x] 模拟晨间信号触发流程。
- [x] 模拟深夜任务错峰启动。
- [x] 验证 API 数据结构。

### 环境验证
- [x] 所有验证必须在 Docker 容器内执行。
- [x] 检查 DDL 执行后的 Schema 完整性。
