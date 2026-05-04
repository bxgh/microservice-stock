# 云端调度系统 (Stock-Manager-Scheduler) 开发文档 v1.1

## 1. 架构定位
在股票异动捕捉管线 v1.1 中，云端服务器 (ECS 2C4G) 充当 **"数据门户"** 与 **"状态网关"**。由于内存与 CPU 资源有限，云端严禁执行复杂的因子计算或异动管线，其核心任务是确保 ODS 层数据的完整采集，并为内网计算节点提供就绪信号。

### 1.1 节点职责
- **数据采集**: 每日 15:30 - 20:30 执行日线、资金流、情绪等 20+ 项同步。
- **状态维护**: 管理 `meta_trading_calendar` (交易日历) 与 `meta_data_readiness` (数据就绪契约)。
- **任务分发**: 接收外部请求，并管理云端任务的生命周期。

---

## 2. 核心组件开发标准

### 2.1 交易日过滤机制 (E1)
所有定时任务必须接入 `CalendarService`。
- **实现**: 使用 `@trading_day_only()` 装饰器。
- **逻辑**: 
    - 盘后采集任务: 校验今日是否为交易日。
    - 盘前事件任务: 校验下一日期是否为交易日。
- **代码参考**: `stock-manager-api/app/scheduler/jobs.py` 中的 `check_trading_day` 辅助函数。

### 2.2 数据就绪契约 (E2)
为了解耦云端与内网，引入 `meta_data_readiness` 表。
- **探测器规则**: `readiness_prober` 每 2 分钟扫描 ODS 表记录数。
- **READY 阈值**:
    - `ods_kline_daily`: > 4000 条
    - `ods_l3_capital_flow`: > 3000 条
    - `ads_l1_market_overview`: > 100 条

### 2.3 任务状态机 (E3)
所有任务执行记录必须持久化至 `workflow_runs`。
- **状态流转**: `PENDING` -> `RUNNING` -> `SUCCESS` / `FAILED`。
- **自愈**: 系统检测到 `RUNNING` 超过 2 小时的任务应标记为 `FAILED` 并触发告警。

---

## 3. 云端任务执行矩阵 (T-Catalog)

| 任务 ID | 执行时间 | 部署位置 | 装饰器类型 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `daily_suspension_morning_sync` | 09:15 | 云端 | `check_next=True` | 早盘停复牌数据 |
| `daily_market_data_sync` | 19:00 | 云端 | `check_next=False` | 主行情同步 (AkShare) |
| `daily_l2_structural_sync` | 19:15 | 云端 | `check_next=False` | 指数与衍生同步 |
| `daily_market_overview_sync` | 19:30 | 云端 | `check_next=False` | L1 全景基础同步 |
| `readiness_prober` | 19:00-23:00 | 云端 | 始终执行 | 就绪状态维护 |
| `daily_audit` | 23:30 | 云端 | 始终执行 | 日终健康度审计 |

---

## 4. 资源约束与性能标准

### 4.1 内存防御红线 (Memory Hard Limit)
- **单任务上限**: 800 MB。
- **措施**: 严禁在云端使用 `pd.merge()` 进行全量大表关联。
- **工具**: 推荐使用生成器或 `Chunking` 模式读写数据库。

### 4.2 API 调用规范
- **重试机制**: 3 次指数退避 (60s, 180s, 600s)。
- **超时设置**: 外部调用 (HTTTP) 强制设置 `timeout=30s`。
- **降级**: 当 Tushare 积分不足或 AkShare 频率受限时，记录 `PARTIAL` 状态。

---

## 5. 监控与告警体系

### 5.1 告警级别
- **WARN**: 单次任务重试成功、数据同步延迟 > 30 分钟。
- **ERROR**: 关键采集任务 (K线) 最终失败、云端数据库连接超时。
- **CRITICAL**: 调度器进程崩溃、连续 2 日无数据产出。

### 5.2 告警渠道
- **邮件**: 通过 aiosmtplib 向运维团队发送详细 Stacktrace。
- **本地日志**: `/app/logs/scheduler_errors.log`。

---

## 6. 维护路线图 (Week 1-2)
- [x] CalendarService 实现交易日过滤逻辑。
- [x] 修正 IndicatorService SQL 语法错误。
- [x] 创建 `meta_data_readiness` 数据契约表。
- [x] 接入 E6 邮件告警体系 (Alerter + System Jobs)。
