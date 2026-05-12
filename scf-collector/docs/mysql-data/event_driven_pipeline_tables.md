# 事件驱动管线核心表字典 (Event-Driven Pipeline Tables)

本方案文档定义了支持“任务交接事件化”架构所需的元数据表，为 SCF 探测器和工作流开发提供物理依据。

---

## 1. 数据就绪探测表 (`meta_data_readiness`)
**用途**: 充当管线中的“信号灯”。上游采集任务完成后，必须在此表留痕，下游任务才能感知并启动。

| 字段 | 类型 | 含义 | 备注 |
| :--- | :--- | :--- | :--- |
| `table_name` | VARCHAR | 数据表名 | e.g. `stock_kline_daily` |
| `biz_date` | DATE | 数据业务日期 | 探测的核心维度 |
| `status` | VARCHAR | 就绪状态 | 必须为 `READY` 才触发下游 |
| `record_count` | INT | 记录行数 | 用于初级数据审计 |
| `ready_at` | TIMESTAMP | 就绪时间 | 下游触发的时间基准 |

---

## 2. 任务执行流水表 (`meta_pipeline_run`)
**用途**: 记录每一个具体的 Pipeline（如“日线采集”、“技术指标计算”）的运行状态，实现断点续传和幂等保护。

| 字段 | 类型 | 含义 | 备注 |
| :--- | :--- | :--- | :--- |
| `run_id` | VARCHAR | 运行唯一标识 | SCF RequestId |
| `pipeline_id` | VARCHAR | 管线 ID | e.g. `Data-Hub`, `Indicator-Calc` |
| `status` | VARCHAR | 状态 | `SUCCESS` / `FAILED` / `RUNNING` |
| `error_message` | TEXT | 错误堆栈 | 故障排查核心依据 |
| `started_at` | TIMESTAMP | 开始时间 | - |

---

## 3. 跨网指令队列 (`task_commands`)
**用途**: SCF 云端与内网服务器 (Node-41) 的通讯桥梁。云端只需在此表中“下单”，内网服务器即可感应并“接单”。

| 字段 | 类型 | 含义 | 备注 |
| :--- | :--- | :--- | :--- |
| `command_type` | VARCHAR | 指令类型 | e.g. `START_COMPUTE`, `RELOAD_CACHE` |
| `payload` | JSON | 指令参数 | 包含业务日期、代码范围等 |
| `is_executed` | TINYINT | 是否已执行 | 0(未执行) / 1(已执行) |
| `executed_at` | TIMESTAMP | 执行时间 | 反馈执行进度 |

---

## 4. 开发约束 (Development Constraints)
1. **就绪检测逻辑**: 探测器必须同时检查 `meta_data_readiness` (是否有数据) 和 `meta_pipeline_run` (是否已经跑过且成功)。
2. **幂等性要求**: 在写入 `task_commands` 前，必须通过 `pipeline_run` 确认该日期该任务尚未成功。
