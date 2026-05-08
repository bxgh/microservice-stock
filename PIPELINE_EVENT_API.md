# 数据管线事件驱动与流水线编排 API (Pipeline & Event-Driven)

> **归属仓**: 腾讯云端服务仓 (Cloud Service)
> **核心逻辑**: 负责从外部源就绪探测 (Probing) 到内网任务指令 (Handover) 的全链路编排。

---

## 1. 流水线阶段定义 (Lifecycle Stages)

流水线按序执行，前置阶段成功后自动触发后续阶段：

| 阶段代码 | 描述 | 触发条件 | 产出物 |
| :--- | :--- | :--- | :--- |
| **STAGE_A_COLLECTION** | 基础数据采集 | Canary 探测 (茅台 K 线) 就绪 | `ods_stock_kline_daily` (MySQL) |
| **STAGE_B_SYNTHESIS** | 指标合成与 L1/L2 | Stage A 且 K 线总行数 > 95% | ClickHouse 明细 / `ads_*` 表 |
| **STAGE_C_AUDIT** | 数据审计 (Gate-3) | Stage B 完成 | 审计通过报告 |
| **STAGE_D_HANDOVER** | 跨网任务接力 | Stage C 审计通过 | `task_commands` (指令下发) |

---

## 2. 状态监控接口 (Monitoring)

### 2.1 查询流水线运行记录
**GET** `/api/v1/pipelines/runs`

*   **参数**:
    *   `biz_date` (Optional): 业务日期 (YYYY-MM-DD)
    *   `status` (Optional): 状态 (RUNNING/SUCCESS/FAILED/PARTIAL)
*   **用途**: 查看今日各个阶段的执行情况、耗时及报错信息。

### 2.2 获取每日统计简报
**GET** `/api/v1/pipelines/stats`

*   **参数**: `biz_date` (Required)
*   **用途**: 快速获取今日任务的总数、成功数和失败数。

---

## 3. 手动干预与触发 (Emergency Control)

### 3.1 手动激活流水线阶段
**POST** `/api/v1/pipelines/runs`

*   **Query 参数**:
    *   `stage_name` (Required): `STAGE_A_COLLECTION`, `STAGE_B_SYNTHESIS`, `STAGE_C_AUDIT`, `STAGE_D_HANDOVER`
    *   `biz_date` (Required): 业务日期
*   **用途**: 当外部数据探测器失效，或需要重跑某一阶段时，调用此接口可强制后台执行。

---

## 4. 任务指令下发 (Cross-Network Handover)

### 4.1 监控下发指令
**GET** `/api/v1/task_commands`

*   **关键任务 ID 说明**:
    *   **标准 ID**: `anomaly_v11` (设计文档规范)
    *   **内网注册名**: `daily_anomaly_scoring` (Node-41 Worker 当前使用的 ID)
    *   **兼容性提示**: 如遇到“未在本地注册”报错，请确认下发 ID 与内网 `TaskRegistry` 匹配。

---

## 5. 运维操作指导

### 5.1 探测阈值调整
当前 K 线就绪判定的动态阈值为：**当日上市股票总数的 95%**。
如需调整比例，修改 `app/scheduler/system_jobs.py` 中的 `kline_min_threshold` 逻辑。

### 5.2 数据库表参考
所有运行状态持久化于 `meta_pipeline_run` 表。该表包含标准“三件套”字段 (`is_deleted` 等)，查询时必须过滤。
