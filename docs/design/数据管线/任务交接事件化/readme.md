# 第 4.1 章 · 任务交接事件化 (Event-Driven Handover)

> **当前状态**: ✅ 实施已完成
> **目标**: 将基于硬编码时间的调度升级为基于数据就绪契约 (Gate-3) 的事件驱动架构。
> **核心原则**: 云端内部任务自动化接力，跨网指令严密触发。

---

## E4 · 任务状态机与编排底座 (Foundation)
**目标**: 补齐 `meta_pipeline_run` 与执行状态的持久化能力，为全局任务流提供真源。

### E4-S1 · meta_pipeline_run 状态追踪
- [x] **E4-S1-T1**: 数据库表结构就绪。
- [x] **E4-S1-T2**: 封装任务状态查询接口 (Runs/Stats)。

---

## E5 · 云端任务编排与连贯性实现 (Orchestration)
**目标**: 彻底梳理 15:00 后的云端任务流程，实现全自动化流水线。

### E5-S1 · 云端四阶段流水线管理器
**设计思路**: 将任务分为四个接力阶段，利用 `WorkflowWatcher` 消除 Cron 等待时延。

| 阶段 | 核心任务 | 准入条件 (Given) | 动作 (When/Then) |
|---|---|---|---|
| **A. 基础采集** | K线/指数/停复牌同步 | **Canary 探测** (Tushare) | 触发数据采集任务并更新契约 |
| **B. 核心综述** | L1 综述 + L2 因子计算 | Stage A 成功 (核心就绪) | 执行 `IndicatorService` 计算逻辑 |
| **C. 质量审计** | 业务校验 + 审计 | Stage B 成功 (综述就绪) | 顺序触发 RuleCheck -> DailyAudit |
| **D. 跨网接力** | 下发内网计算指令 | Stage C 审计通过 (Success) | 写入 `task_commands` |

#### 任务
- [x] **E5-S1-T1**: 实现 `WorkflowManager` 服务，定义任务阶段转换逻辑。
- [x] **E5-S1-T2**: 改造 `readiness_prober`，使其在检测到状态变化时主动触发 `WorkflowManager`。
- [x] **E5-S1-T3**: 指令格式标准化：`{"task_id": "anomaly_v11", "params": {"biz_date": "YYYY-MM-DD", "mode": "event"}}`。

#### 验收标准 (AC)
1. **Given** 19:05 核心数据已就绪 **When** 探测器发现 **Then** 立即触发“业务校验”，验证通过后立即触发“数据审计”。
2. **Given** 云端审计通过 **When** 进入阶段 D **Then** `task_commands` 出现 PENDING 指令。

---

## E6 · 迁移与鲁棒性增强 (Migration & Safety)
**目标**: 安全移除存量 Cron，建立保底机制。

### E6-S1 · 任务触发模式切换
- [x] **E6-S1-T1**: 移除 `app/main.py` 中关于审计与日终计算的冗余 Cron 定时配置。
- [x] **E6-S1-T2**: 部署 `WorkflowManager` 并开启实时监控日志。
- [x] **E6-S1-T3**: **[安全性]** 建立保底 Cron (Safety Cron)，于 23:00 执行强制扫描，防止因信号丢失导致的漏跑。

#### 验收标准 (AC)
1. **Given** 事件流正常 **When** 21:00 前完成所有任务 **Then** 系统无空转，时延较 Cron 模式降低 1-2 小时。
2. **Given** 极端异常导致流程中断 **When** 23:00 **Then** 保底 Cron 能够识别并重启流水线。

