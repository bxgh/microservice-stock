# 股票异动捕捉管线 v1.1 部署方案

**文档版本**:v1.1
**最后更新**:2026-05-05
**作者**:架构组
**状态**:进行中 (已完成基础底座建设)

---

## 文档说明

### 背景

现有微服务股票数据系统已稳定运行,具备以下能力:

- **云端**:腾讯云 ECS(2核4G)+ 云 MySQL(1核1G)运行 4 个微服务,负责数据采集与存储
- **内网**:已打通 SSH 隧道,内网服务器运行 pytdx 盘中数据采集,数据落地内网 ClickHouse
- **基础调度**:`stock-manager` 内运行 APScheduler,21+ 个定时任务

存在的问题:

- 缺乏交易日感知,非交易日产生无效负载与错误日志
- 2026-05-02 主流水线因 SQL 参数 Bug 失败,L2 指标缺失(已修复但暴露调度脆弱性)
- 计划新增的异动捕捉管线(9 张表 / 8 个 task)资源消耗高,纯云端部署不可行
- 缺乏数据就绪契约、任务状态机、断点续跑、告警等生产级保障

### 目标

构建一条**稳定、可观测、当天可出结果**的异动捕捉管线,集成到现有调度体系。具体要求:

- 交易日 21:00 前完成当日异动榜单产出并回写云端
- 非交易日自动跳过,无错误日志
- 关键失败有邮件告警,可定位、可重跑
- 现有任务体系不受影响,改造工作量可控

### 范围

**包含**:

- 异动管线 8 个 task 的部署位置与编排
- CalendarService 实现与全局接入
- 数据就绪契约(`meta_data_readiness`)
- 任务状态机(`meta_pipeline_run`)
- 跨网数据同步与结果回写
- 邮件告警体系
- 现有任务的交易日装饰器改造

**不包含(非目标)**:

- ClickHouse 性能调优(现有 CK 性能足够,等出问题再优化)
- WireGuard 替换 SSH 隧道(SSH 隧道稳定运行,不动)
- 升级云 MySQL 配置(内网承担计算后云端压力降低)
- ELK / Loki 集中日志(邮件 + 文件日志先满足)
- 异地多活 / 高可用(当前规模不需要)
- 异动管线 v1.2 命中率自学习(看后续业务规划)

---

## 当前实施进度 (2026-05-05)

### 前置依赖：历史数据校验体系 (DQ System) —— **[100% 已就绪]**
*基础底座（校验规则、补数闭环、可观测性）已全面交付，为异动管线提供数据信心。*

### 核心任务：异动捕捉管线部署 (Pipeline Deployment v1.1)
- [x] **E1 · CalendarService**: 已完成接入。
- [x] **E2 · 数据就绪契约**: 已上线。
- [x] **E3 · 任务状态机**: 已验证。
- [/] **E4 · 跨网数据同步**: **[本周重点]** `CloudDataSyncer` 开发中。
- [/] **E5 · 计算调度**: 异动算法 task 编排与 `stock-compute` 节点联调中。
- [ ] **E6-E8 · 告警与实施**: 待启动。

---

### 节点与职责

| 节点 | 配置 | 职责 |
|---|---|---|
| 云端 ECS | 2核4G / SSD 70G / 6Mbps | 数据采集、ODS 写入、对外 API、读屏障 |
| 云 MySQL | 1核1G / 2400 IOPS | 数据真源、采集结果存储、计算结果归档、状态元数据 |
| 内网服务器 | 资源充足(8核16G+) | 计算密集任务、异动管线、L1/L2 因子 |
| 内网 ClickHouse | 已部署 | 盘中分钟/Tick 数据(pytdx 采集) |
| 内网 MySQL 副本 | **新增**(后续部署) | 云端日终数据的本地副本,供内网计算读取 |
| 网络通道 | SSH 隧道(autossh + systemd) | 已打通,稳定运行 |

### 数据分层

| 层 | 内容 | 主存储 | 副本 |
|---|---|---|---|
| ODS | 原始采集数据(行情、财务、公告) | 云 MySQL | 内网 MySQL 副本(增量同步) |
| 盘中实时层 | 分钟 K 线、分时、Tick | **内网 CK** | 不副本(数据量大且只用于实时计算) |
| ADS-L1 | 市场全景、广度、指数 | 内网计算 → 双写云 + 内网 | — |
| ADS-L2 | 行业 / 概念 / 风格因子 | 内网计算 → 双写云 + 内网 | — |
| ADS-L8 | 异动信号(基础信号 + 派生指标) | 内网计算 → 双写云 + 内网 | — |
| APP | 异动 Top10 推送 | 内网计算 → 双写云 + 内网 | 前端读云端 |
| META | 数据就绪 / 任务状态 / 交易日历 | 云 MySQL(权威) | 内网读云端 |

### 任务分布

| 类别 | 部署节点 | 任务示例 |
|---|---|---|
| 数据采集 | 云端 | `daily_market_data_sync`、财务系列、公告系列、`weekly_*` |
| 盘前事件 | 云端 | `daily_performance_forecast_sync`、`daily_suspension_morning_sync` |
| 盘中采集 | 内网 | pytdx → CK(已运行) |
| 盘后采集 | 云端 | `daily_kline_watcher`、`daily_etf_kline_sync` |
| 资金面采集 | 云端 | `daily_monitor_data_sync` |
| L1/L2 因子计算 | **内网** | 从云端 `stock-manager` 迁移到内网 `stock-compute` |
| 监控指标计算 | **内网** | `daily_monitor_calculate` |
| 异动管线 | **内网** | 8 个新 task |
| 调度入口 / API | 云端 | 现有 `stock-manager` 保留,负责对外 |
| 计算调度 | **内网** | 新增 `stock-compute` 内置 APScheduler |

---

## E1 · CalendarService 与交易日装饰器

### E1-S1 数据模型

**作为** 全系统,**我希望** 通过统一接口判定任意日期是否为交易日,**以便** 杜绝非交易日产生的无效负载和错误日志。

云 MySQL 上创建交易日历表:

```sql
CREATE TABLE meta_trading_calendar (
    cal_date        DATE PRIMARY KEY,
    is_trading_day  TINYINT NOT NULL,           -- 1=交易日, 0=非交易日
    market          VARCHAR(8) DEFAULT 'CN',    -- CN / HK / US
    prev_trading    DATE,                        -- 前一交易日(交易日才填)
    next_trading    DATE,                        -- 下一交易日
    week_of_year    INT,
    is_month_end    TINYINT DEFAULT 0,           -- 是否当月最后交易日
    is_quarter_end  TINYINT DEFAULT 0,
    holiday_name    VARCHAR(64),                 -- 假日名(非交易日才填)
    INDEX idx_trading (is_trading_day, cal_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

初始化数据从 Tushare `pro.trade_cal` 拉取未来 3 年。

### E1-S2 服务实现

```python
# stock_manager/services/calendar_service.py
from datetime import date, timedelta

class CalendarService:
    """交易日历服务,三级缓存,极少打扰数据库"""

    def __init__(self, db, redis):
        self.db = db
        self.redis = redis
        self._mem_cache: dict[date, bool] = {}

    async def is_trading_day(self, target: date) -> bool:
        # L1 进程内
        if target in self._mem_cache:
            return self._mem_cache[target]

        # L2 Redis(7 天 TTL)
        key = f"cal:trading:{target.isoformat()}"
        cached = await self.redis.get(key)
        if cached is not None:
            result = cached == b"1"
            self._mem_cache[target] = result
            return result

        # L3 MySQL
        row = await self.db.fetch_one(
            "SELECT is_trading_day FROM meta_trading_calendar WHERE cal_date=%s",
            (target,)
        )
        if row is None:
            raise ValueError(f"日历无 {target} 数据,需扩展日历范围")

        result = bool(row["is_trading_day"])
        await self.redis.setex(key, 86400 * 7, b"1" if result else b"0")
        self._mem_cache[target] = result
        return result

    async def get_prev_trading_day(self, target: date) -> date:
        row = await self.db.fetch_one(
            "SELECT prev_trading FROM meta_trading_calendar "
            "WHERE cal_date=%s AND is_trading_day=1",
            (target,)
        )
        if row is None or row["prev_trading"] is None:
            # 回退查询:找小于 target 的最大交易日
            row = await self.db.fetch_one(
                "SELECT MAX(cal_date) AS d FROM meta_trading_calendar "
                "WHERE cal_date < %s AND is_trading_day=1",
                (target,)
            )
            return row["d"]
        return row["prev_trading"]

    async def get_next_trading_day(self, target: date) -> date:
        row = await self.db.fetch_one(
            "SELECT MIN(cal_date) AS d FROM meta_trading_calendar "
            "WHERE cal_date >= %s AND is_trading_day=1",
            (target,)
        )
        return row["d"]
```

### E1-S3 装饰器

```python
# stock_manager/common/scheduler_decorators.py
from functools import wraps
from datetime import date

def trading_day_only(check_next: bool = False):
    """
    交易日装饰器
    - check_next=False:校验今日(收盘后行情计算类)
    - check_next=True:校验下一交易日(盘前事件类)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            today = date.today()
            target = (await calendar_service.get_next_trading_day(today)
                      if check_next else today)
            is_trading = await calendar_service.is_trading_day(target)

            if not is_trading:
                logger.info(f"[{func.__name__}] 跳过:{target} 非交易日")
                return {"status": "SKIPPED", "reason": "non_trading_day"}

            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### E1-S4 装饰器接入矩阵

| 任务 ID | 装饰器 | 说明 |
|---|---|---|
| `daily_market_data_sync` | `@trading_day_only()` | 行情采集 |
| `daily_l2_structural_sync` | `@trading_day_only()` | 行情衍生 |
| `daily_market_overview_sync` | `@trading_day_only()` | 核心流水线 |
| `daily_sentiment_sync` | `@trading_day_only()` | 情绪指标 |
| `daily_etf_kline_sync` | `@trading_day_only()` | ETF 行情 |
| `daily_kline_watcher` | `@trading_day_only()` | K 线监测 |
| `daily_monitor_data_sync` | `@trading_day_only()` | 资金面 |
| `daily_monitor_calculate` | `@trading_day_only()` | 监控计算 |
| `daily_suspension_morning_sync` | `@trading_day_only(check_next=True)` | 盘前事件,看下一交易日 |
| `anomaly_v11_pipeline` | `@trading_day_only()` | 异动管线 |
| `daily_performance_forecast_sync` | ❌ 不加 | 财报随时披露 |
| `daily_finance_indicators_sync` | ❌ 不加 | 财务指标 |
| `daily_analyst_rating_sync` | ❌ 不加 | 评级数据 |
| `daily_shareholder_sync` | ❌ 不加 | 股东数据 |
| `daily_financial_incremental_sync` | ❌ 不加 | 财报增量 |
| `weekly_*` 系列 | ❌ 不加 | 周末任务 |
| `health_check` / `*_heartbeat` | ❌ 不加 | 监控类必须始终跑 |

### E1-S5 日历自动维护

```python
# stock_manager/scheduler/jobs/calendar_maintenance.py
@scheduler.scheduled_job("cron", day=1, hour=3, minute=0,
                         id="maintain_calendar")
async def maintain_calendar():
    """每月 1 号 03:00 检查日历,自动从 Tushare 补齐未来 3 年"""
    today = date.today()
    target_end = today.replace(year=today.year + 3)

    last = await db.fetch_val(
        "SELECT MAX(cal_date) FROM meta_trading_calendar"
    )
    if last and last >= target_end:
        return

    df = pro.trade_cal(
        exchange='SSE',
        start_date=(last or today).strftime("%Y%m%d"),
        end_date=target_end.strftime("%Y%m%d"),
    )
    await batch_upsert_calendar(df)
    await alerter.alert("INFO", f"日历已扩展至 {target_end}")
```

### E1-S6 验收标准

- **Given** 当前是周六(非交易日)
- **When** 19:30 调度器触发 `daily_market_overview_sync`
- **Then** 任务返回 `{"status": "SKIPPED", "reason": "non_trading_day"}`,日志记录,不调用任何外部 API,不写数据库

- **Given** 日历表最大日期距今不足 1 年
- **When** 月度维护任务触发
- **Then** 自动从 Tushare 补齐至未来 3 年,发送 INFO 告警

---

## E2 · 数据就绪契约

### E2-S1 数据模型

**作为** 内网计算节点,**我希望** 通过查询元数据表获知云端数据是否就绪,**以便** 不再依赖脆弱的时间假设。

云 MySQL 上创建就绪契约表:

```sql
CREATE TABLE meta_data_readiness (
    table_name      VARCHAR(128) NOT NULL,
    biz_date        DATE NOT NULL,
    storage         VARCHAR(16) DEFAULT 'cloud_mysql',  -- cloud_mysql / internal_ck / internal_mysql
    record_count    BIGINT,                              -- 实际记录数
    expected_min    BIGINT DEFAULT 0,                    -- 预期最小记录数
    producer_node   VARCHAR(64),                          -- cloud / internal
    producer_task   VARCHAR(128),                         -- 产出任务 ID
    ready_at        DATETIME,                              -- 就绪时间戳
    status          VARCHAR(16),                           -- READY / PARTIAL / PENDING / FAILED
    notes           VARCHAR(255),                           -- 状态附加说明
    PRIMARY KEY (table_name, biz_date),
    INDEX idx_biz_status (biz_date, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### E2-S2 旁路探测器(零侵入兜底)

不修改现有上游采集任务,通过旁路扫描自动维护就绪状态:

```python
# stock_manager/scheduler/jobs/readiness_prober.py
PROBE_RULES = {
    # table:                    (biz_date_field,  min_rows)
    "ods_kline_daily":          ("trade_date",    4000),
    "ads_l1_market_overview":   ("trade_date",    100),
    "ods_l3_capital_flow":      ("trade_date",    3000),
    "ods_l4_sentiment":         ("biz_date",      5),
    "ods_l6_event":             ("biz_date",      0),    # 可能为空
    "ads_l8_unified_signal":    ("biz_date",      100),
    "ods_etf_kline":            ("trade_date",    500),
    "ods_market_sentiment":     ("biz_date",      1),
}

@scheduler.scheduled_job(
    "interval", minutes=2,
    id="readiness_prober",
)
@trading_day_only()
async def probe_readiness():
    """交易日 19:00-23:00 每 2 分钟探测一次"""
    now = datetime.now()
    if not (time(19, 0) <= now.time() <= time(23, 0)):
        return

    biz_date = date.today()
    for table, (date_field, min_rows) in PROBE_RULES.items():
        try:
            row_count = await db.fetch_val(
                f"SELECT COUNT(*) FROM {table} WHERE {date_field}=%s",
                (biz_date,)
            )
            status = (
                "READY" if row_count >= min_rows
                else "PARTIAL" if row_count > 0
                else "PENDING"
            )
            await db.execute("""
                INSERT INTO meta_data_readiness
                (table_name, biz_date, storage, record_count, expected_min,
                 producer_node, ready_at, status)
                VALUES (%s, %s, 'cloud_mysql', %s, %s, 'cloud', NOW(), %s)
                ON DUPLICATE KEY UPDATE
                    record_count=VALUES(record_count),
                    ready_at=VALUES(ready_at),
                    status=VALUES(status)
            """, (table, biz_date, row_count, min_rows, status))
        except Exception as e:
            logger.error(f"探测 {table} 失败: {e}")
```

### E2-S3 主动写入(新任务规范)

**所有新任务**(包括异动管线、L1/L2 计算、内网回写)必须在事务结尾主动写入就绪状态:

```python
async def writeback_with_readiness(
    biz_date: date,
    table: str,
    records: list[dict],
    producer_task: str,
    producer_node: str = "internal",
):
    async with cloud_db.transaction() as tx:
        # 1. 删除当日旧数据(幂等)
        await tx.execute(f"DELETE FROM {table} WHERE biz_date=%s", (biz_date,))

        # 2. 批量写入
        await tx.executemany(build_insert_sql(table), records)

        # 3. 写入就绪状态
        await tx.execute("""
            INSERT INTO meta_data_readiness
            (table_name, biz_date, storage, record_count, producer_node,
             producer_task, ready_at, status)
            VALUES (%s, %s, 'cloud_mysql', %s, %s, %s, NOW(), 'READY')
            ON DUPLICATE KEY UPDATE
                record_count=VALUES(record_count),
                producer_task=VALUES(producer_task),
                ready_at=VALUES(ready_at),
                status='READY'
        """, (table, biz_date, len(records), producer_node, producer_task))
```

### E2-S4 内网就绪等待器

```python
# stock_compute/scheduler/cloud_readiness_watcher.py
REQUIRED_FOR_ANOMALY = [
    ("ads_l1_market_overview", True),    # critical
    ("ods_l3_capital_flow",    True),
    ("ods_l4_sentiment",       False),    # non-critical, 可降级
    ("ods_l6_event",           False),
    ("ads_l8_unified_signal",  True),
    ("ads_l2_structural",      True),
]

async def check_cloud_readiness(biz_date: date) -> tuple[bool, list, list]:
    """
    返回: (是否全部 READY, 缺失关键表, 缺失非关键表)
    """
    critical_missing = []
    non_critical_missing = []

    async with cloud_conn_manager.session() as conn:
        for table, is_critical in REQUIRED_FOR_ANOMALY:
            row = await conn.fetch_one(
                "SELECT status, record_count FROM meta_data_readiness "
                "WHERE table_name=%s AND biz_date=%s",
                (table, biz_date)
            )
            ready = row and row["status"] == "READY"
            if not ready:
                target = critical_missing if is_critical else non_critical_missing
                target.append(f"{table}: {row['status'] if row else 'PENDING'}")

    all_ready = not critical_missing and not non_critical_missing
    return all_ready, critical_missing, non_critical_missing
```

### E2-S5 验收标准

- **Given** 云端 `daily_market_data_sync` 正在执行,数据写入中
- **When** 旁路探测器扫描该表
- **Then** 状态为 `PARTIAL` 或 `PENDING`,不会标记为 `READY`

- **Given** 云端所有 ODS 表均已就绪
- **When** 内网调用 `check_cloud_readiness`
- **Then** 返回 `(True, [], [])`,异动管线可启动

---

## E3 · 任务状态机与编排

### E3-S1 数据模型

**作为** 调度系统,**我希望** 任务执行状态持久化,**以便** 进程崩溃后能从断点续跑,失败任务能被识别和重试。

```sql
CREATE TABLE meta_pipeline_run (
    run_id          VARCHAR(64) NOT NULL,            -- 一次管线运行的唯一标识
    pipeline_id     VARCHAR(128) NOT NULL,           -- 管线 ID(如 anomaly_v11)
    biz_date        DATE NOT NULL,
    task_id         VARCHAR(128) NOT NULL,           -- 任务 ID
    status          VARCHAR(16) NOT NULL,            -- PENDING / RUNNING / SUCCESS / FAILED / SKIPPED
    started_at      DATETIME,
    finished_at     DATETIME,
    duration_sec    INT,
    retry_count     INT DEFAULT 0,
    max_retry       INT DEFAULT 1,
    error_message   TEXT,
    error_stack     TEXT,
    output_summary  JSON,                             -- 任务输出摘要(行数、关键指标)
    PRIMARY KEY (run_id, task_id),
    INDEX idx_pipeline_biz (pipeline_id, biz_date),
    INDEX idx_status (status, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### E3-S2 PipelineRunner 实现

```python
# stock_compute/scheduler/pipeline_runner.py
class PipelineRunner:
    """通用管线执行器,支持依赖、超时、重试、断点续跑"""

    def __init__(self, pipeline_id: str, tasks: list[dict]):
        self.pipeline_id = pipeline_id
        self.tasks = tasks
        self._task_map = {t["task_id"]: t for t in tasks}

    async def run(self, biz_date: date, mode: str = "normal"):
        run_id = f"{self.pipeline_id}_{biz_date.isoformat()}"

        # 全局闸门:整个管线占据,期间其他重任务等待
        async with global_gate.heavy_task(run_id, timeout=3600):
            ordered = self._topo_sort()

            for task in ordered:
                # 断点续跑:已成功跳过
                if await self._is_done(run_id, task["task_id"]):
                    logger.info(f"[skip] {task['task_id']} 已完成")
                    continue

                # 检查依赖
                if not await self._check_deps(run_id, task.get("depends_on", [])):
                    if mode == "degraded" and task.get("degradable"):
                        await self._mark_skipped(run_id, task["task_id"], biz_date,
                                                  reason="degraded")
                        continue
                    raise PipelineDepsFailedError(task["task_id"])

                # 执行(带重试)
                await self._execute_with_retry(run_id, task, biz_date)

    async def _execute_with_retry(self, run_id: str, task: dict, biz_date: date):
        max_retry = task.get("retry", 1)
        timeout = task.get("timeout_sec", 600)

        for attempt in range(max_retry + 1):
            await self._mark_running(run_id, task["task_id"], biz_date, attempt)
            start = time.time()
            try:
                if task["type"] == "python":
                    await self._run_python(task, biz_date, timeout)
                elif task["type"] == "python_isolated":
                    await self._run_python_isolated(task, biz_date, timeout)
                elif task["type"] == "sql":
                    await self._run_sql(task, biz_date, timeout)
                else:
                    raise ValueError(f"unknown task type: {task['type']}")

                await self._mark_success(run_id, task["task_id"],
                                          duration=time.time() - start)
                return
            except Exception as e:
                logger.error(f"[{task['task_id']}] attempt {attempt+1} failed: {e}")
                if attempt < max_retry:
                    interval = task.get("retry_interval", 60)
                    await asyncio.sleep(interval)
                    continue

                await self._mark_failed(run_id, task["task_id"], biz_date,
                                         error=str(e), stack=traceback.format_exc())
                await alerter.alert("ERROR", f"任务失败 {task['task_id']}", {
                    "biz_date": biz_date.isoformat(),
                    "error": str(e),
                })
                raise

    async def _run_python_isolated(self, task: dict, biz_date: date, timeout: int):
        """子进程隔离执行,带内存上限"""
        cmd = [
            "prlimit", f"--as={task.get('mem_limit_mb', 1500) * 1024 * 1024}",
            "--",
            "python", "-u", task["script"],
            "--biz-date", biz_date.isoformat(),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            if proc.returncode != 0:
                raise TaskExecutionError(stderr.decode()[:2000])
            return stdout.decode()
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise TaskTimeoutError(f"{task['script']} 超时 {timeout}s")
```

### E3-S3 全局闸门

```python
# stock_compute/common/global_gate.py
class GlobalTaskGate:
    """整个内网计算节点同时只允许 1 个重任务运行"""

    GATE_KEY = "task_gate:heavy"

    @asynccontextmanager
    async def heavy_task(self, task_id: str, timeout: int = 1800):
        lock = redis_client.lock(
            self.GATE_KEY,
            timeout=timeout,
            blocking_timeout=3600,
        )
        acquired = await lock.acquire()
        if not acquired:
            raise TaskGateTimeout(f"{task_id} 等待闸门超时")

        start = time.time()
        try:
            logger.info(f"[gate] {task_id} 获得执行权")
            yield
        finally:
            await lock.release()
            logger.info(f"[gate] {task_id} 释放,耗时 {time.time()-start:.1f}s")
```

### E3-S4 验收标准

- **Given** 异动管线执行到 task 5 时进程崩溃
- **When** 调度器重新触发同一 biz_date 的管线
- **Then** task 1-4 标记为 SUCCESS,自动跳过,从 task 5 继续执行

- **Given** task 因瞬时网络抖动失败
- **When** 配置 `retry=2, retry_interval=60`
- **Then** 60 秒后自动重试,最多重试 2 次,全部失败才标记 FAILED

---

## E4 · 跨网数据同步

### E4-S1 同步策略

| 表类型 | 同步方式 | 频率 | 触发 |
|---|---|---|---|
| ODS 日终行情(K线/资金流/情绪) | 增量按日期分区 | 计算前 | 内网 watcher 主动拉 |
| ADS 元数据 | 全量覆盖 | 每周 | 周日凌晨 |
| 元数据(股票池/行业映射) | 全量覆盖 | 每日 | 内网计算前 |
| `meta_trading_calendar` | 增量 | 每月 | 内网启动时校验 |
| `meta_data_readiness` | 不同步 | 实时 | 直连云端查询 |

### E4-S2 增量同步器

```python
# stock_compute/sync/cloud_to_local.py
class CloudDataSyncer:
    """云端 → 内网 MySQL 副本 增量同步"""

    SYNC_TABLES = {
        # table: (biz_date_field, retain_days)
        "ods_kline_daily":          ("trade_date", 90),
        "ads_l1_market_overview":   ("trade_date", 60),
        "ods_l3_capital_flow":      ("trade_date", 30),
        "ods_l4_sentiment":         ("biz_date",   30),
        "ads_l8_unified_signal":    ("biz_date",   30),
        "ods_l6_event":             ("biz_date",   30),
        "ads_l2_structural":        ("biz_date",   30),
        "ods_etf_kline":            ("trade_date", 60),
    }

    FULL_SYNC_TABLES = [
        "meta_stock_basic",
        "meta_industry_mapping",
        "meta_concept_mapping",
        "meta_trading_calendar",
    ]

    async def sync_for_compute(self, biz_date: date):
        """计算前的完整同步流程"""
        # 1. 全量元数据(每日刷新)
        for table in self.FULL_SYNC_TABLES:
            await self._sync_full(table)

        # 2. 增量行情数据
        for table, (date_field, retain) in self.SYNC_TABLES.items():
            local_max = await self._get_local_max_date(table, date_field)
            start = (local_max + timedelta(days=1)) if local_max \
                    else (biz_date - timedelta(days=retain))
            await self._sync_incremental(table, date_field, start, biz_date)
            await self._purge_old(table, date_field, retain)

        # 3. 同步 readiness 当日记录(用于内网状态判断)
        await self._sync_readiness_today(biz_date)

    async def _sync_incremental(self, table, date_field, start, end):
        cloud_engine = create_engine(
            f"mysql+pymysql://...?compress=true&charset=utf8mb4"
        )

        current = start
        while current <= end:
            df = pd.read_sql(
                f"SELECT * FROM {table} WHERE {date_field}=%s",
                cloud_engine,
                params=(current,)
            )
            if not df.empty:
                await self._upsert_local(table, df)
                logger.info(f"synced {table} {current}: {len(df)} rows")
            current += timedelta(days=1)
```

### E4-S3 双写回写器

```python
# stock_compute/writeback/dual_write.py
class DualWriter:
    """计算结果双写:内网副本 + 云端 MySQL"""

    async def writeback(
        self,
        biz_date: date,
        table: str,
        records: list[dict],
        producer_task: str,
    ):
        # 1. 先写内网副本(快,几乎不会失败)
        try:
            async with internal_db.transaction() as tx:
                await tx.execute(f"DELETE FROM {table} WHERE biz_date=%s",
                                  (biz_date,))
                await self._batch_insert(tx, table, records)
            logger.info(f"[local] wrote {table} {biz_date}: {len(records)} rows")
        except Exception as e:
            await alerter.alert("ERROR", f"内网回写失败 {table}", {"error": str(e)})
            raise

        # 2. 再写云端(经过隧道,可能慢/失败)
        try:
            async with cloud_db.transaction() as tx:
                await tx.execute(f"DELETE FROM {table} WHERE biz_date=%s",
                                  (biz_date,))
                await self._batch_insert(tx, table, records)
                # 同时更新就绪状态
                await self._update_readiness(tx, table, biz_date,
                                              len(records), producer_task)
            logger.info(f"[cloud] wrote {table} {biz_date}: {len(records)} rows")
        except Exception as e:
            # 云端失败不阻塞内网,但记录到补偿队列
            await alerter.alert("ERROR", f"云端回写失败 {table}", {"error": str(e)})
            await self._enqueue_pending_writeback(table, biz_date, records,
                                                    producer_task)
```

### E4-S4 一致性补偿

```python
# stock_compute/scheduler/jobs/consistency_check.py
@scheduler.scheduled_job("cron", hour=3, minute=0, id="consistency_reconcile")
async def reconcile_cloud_internal():
    """每日 03:00 对账,以内网为准回写云端"""
    biz_date = date.today() - timedelta(days=1)

    KEY_TABLES = [
        "ads_l1_market_overview",
        "ads_l2_structural",
        "ads_l8_unified_signal",
        "ads_anomaly_score",
        "app_anomaly_top10_daily",
    ]

    for table in KEY_TABLES:
        local_count = await internal_db.fetch_val(
            f"SELECT COUNT(*) FROM {table} WHERE biz_date=%s", (biz_date,)
        )
        cloud_count = await cloud_db.fetch_val(
            f"SELECT COUNT(*) FROM {table} WHERE biz_date=%s", (biz_date,)
        )

        if local_count != cloud_count:
            await alerter.alert("WARN", f"对账不一致 {table}", {
                "biz_date": biz_date.isoformat(),
                "local_count": local_count,
                "cloud_count": cloud_count,
            })
            # 重新回写云端
            records = await internal_db.fetch_all(
                f"SELECT * FROM {table} WHERE biz_date=%s", (biz_date,)
            )
            await dual_writer._writeback_cloud_only(biz_date, table, records,
                                                     "consistency_reconcile")
```

### E4-S5 验收标准

- **Given** 内网执行 `sync_for_compute(2026-05-04)`
- **When** 同步开始
- **Then** 8 张行情表 + 4 张元数据表完成增量同步,耗时 ≤ 5 分钟,网络压缩比 ≥ 4:1

- **Given** 内网计算结果回写时,云端连接中断
- **When** 回写云端环节抛异常
- **Then** 内网已完成写入,失败记录入补偿队列,凌晨 03:00 自动重试

---

## E5 · 异动管线

### E5-S1 表结构

异动管线产出 9 张表(具体 DDL 待补充,这里列清单):

| 表名 | 层 | 用途 |
|---|---|---|
| `ads_anomaly_derived_metrics` | ADS | 派生指标(分时强度、加速度、量价配合) |
| `ads_anomaly_market_state` | ADS | 市场状态判定(强势/震荡/弱势) |
| `ads_anomaly_strong_pool` | ADS | 强势池(已突破/有共振) |
| `ads_anomaly_early_pool` | ADS | 早期池(预共振) |
| `ads_anomaly_trap_pool` | ADS | 陷阱池(假突破/诱多) |
| `ads_anomaly_tags` | ADS | 标签云(技术/资金/情绪/事件) |
| `ads_anomaly_resonance` | ADS | 多维印证(共振/对冲/时序) |
| `ads_anomaly_score` | ADS | 综合评分 + 中文说明 |
| `app_anomaly_top10_daily` | APP | Top10 推送 |

### E5-S2 任务定义

```python
# stock_compute/pipelines/anomaly_v11.py
ANOMALY_V11_TASKS = [
    {
        "task_id": "compute_derived_metrics",
        "type": "python_isolated",
        "script": "scripts/anomaly/compute_derived_metrics.py",
        "mem_limit_mb": 1500,
        "timeout_sec": 600,
        "retry": 2,
        "retry_interval": 60,
        "depends_on": [],
        "data_sources": ["internal_ck", "internal_mysql"],  # CK 取分时,MySQL 取日终
        "outputs": ["ads_anomaly_derived_metrics"],
    },
    {
        "task_id": "compute_market_state",
        "type": "python",
        "script": "scripts/anomaly/compute_market_state.py",
        "mem_limit_mb": 300,
        "timeout_sec": 120,
        "retry": 2,
        "depends_on": [],
        "outputs": ["ads_anomaly_market_state"],
    },
    {
        "task_id": "produce_strong_pool",
        "type": "python_isolated",
        "script": "scripts/anomaly/produce_strong_pool.py",
        "mem_limit_mb": 1200,
        "timeout_sec": 360,
        "retry": 1,
        "depends_on": ["compute_derived_metrics", "compute_market_state"],
        "outputs": ["ads_anomaly_strong_pool"],
    },
    {
        "task_id": "compute_early_combo1",
        "type": "sql",
        "file": "sql/anomaly/early_combo1.sql",
        "timeout_sec": 360,
        "retry": 1,
        "depends_on": ["compute_derived_metrics"],
        "degradable": True,
        "outputs": ["ads_anomaly_early_pool"],
    },
    {
        "task_id": "compute_trap_signals",
        "type": "python_isolated",
        "script": "scripts/anomaly/compute_trap.py",
        "mem_limit_mb": 1000,
        "timeout_sec": 360,
        "retry": 1,
        "depends_on": ["compute_derived_metrics"],
        "degradable": True,
        "outputs": ["ads_anomaly_trap_pool"],
    },
    {
        "task_id": "compute_tags",
        "type": "python",
        "script": "scripts/anomaly/compute_tags.py",
        "mem_limit_mb": 600,
        "timeout_sec": 180,
        "retry": 2,
        "depends_on": ["produce_strong_pool", "compute_early_combo1",
                        "compute_trap_signals"],
        "outputs": ["ads_anomaly_tags", "ads_anomaly_resonance"],
    },
    {
        "task_id": "compute_score_composite",
        "type": "sql",
        "file": "sql/anomaly/composite_score.sql",
        "timeout_sec": 180,
        "retry": 2,
        "depends_on": ["compute_tags"],
        "outputs": ["ads_anomaly_score"],
    },
    {
        "task_id": "generate_top10",
        "type": "python",
        "script": "scripts/anomaly/top10.py",
        "mem_limit_mb": 300,
        "timeout_sec": 120,
        "retry": 3,
        "depends_on": ["compute_score_composite"],
        "outputs": ["app_anomaly_top10_daily"],
    },
]
```

### E5-S3 调度入口

```python
# stock_compute/scheduler/jobs/anomaly_trigger.py

@scheduler.scheduled_job(
    "interval", minutes=1,
    id="anomaly_trigger_watcher",
)
@trading_day_only()
async def anomaly_trigger_watcher():
    """20:30-22:00 每分钟检查云端就绪,就绪即触发"""
    now = datetime.now()
    if not (time(20, 30) <= now.time() <= time(22, 0)):
        return

    biz_date = date.today()
    if await is_pipeline_done("anomaly_v11", biz_date):
        return

    all_ready, critical, non_critical = await check_cloud_readiness(biz_date)

    if all_ready:
        logger.info(f"云端数据全部就绪,启动异动管线 {biz_date}")
        await mark_pipeline_started("anomaly_v11", biz_date)
        await run_full_compute_pipeline(biz_date, mode="normal")
    elif not critical:
        # 只缺非关键表,可降级
        logger.warning(f"非关键表缺失 {non_critical},等到 deadline")
    else:
        logger.debug(f"关键表缺失 {critical},继续等待")


@scheduler.scheduled_job(
    "cron", hour=22, minute=0,
    id="anomaly_deadline",
)
@trading_day_only()
async def anomaly_deadline():
    """22:00 死线兜底"""
    biz_date = date.today()
    if await is_pipeline_done("anomaly_v11", biz_date):
        return

    all_ready, critical, non_critical = await check_cloud_readiness(biz_date)

    if all_ready:
        await run_full_compute_pipeline(biz_date, mode="normal")
    elif not critical and non_critical:
        await alerter.alert("WARN", "异动管线降级运行", {
            "biz_date": biz_date.isoformat(),
            "missing": non_critical,
        })
        await run_full_compute_pipeline(biz_date, mode="degraded")
    else:
        await alerter.alert("ERROR", "异动管线跳过", {
            "biz_date": biz_date.isoformat(),
            "critical_missing": critical,
        })
        await mark_pipeline_skipped("anomaly_v11", biz_date,
                                     reason=critical)


async def run_full_compute_pipeline(biz_date: date, mode: str):
    """完整内网计算流程"""
    try:
        # Step 1: 同步云端数据到内网
        logger.info(f"[{biz_date}] 开始同步云端数据")
        await syncer.sync_for_compute(biz_date)

        # Step 2: L1/L2 因子计算(如果尚未完成)
        if not await is_l1_l2_done(biz_date):
            logger.info(f"[{biz_date}] 开始 L1/L2 计算")
            await run_l1_l2_pipeline(biz_date)

        # Step 3: 异动管线
        logger.info(f"[{biz_date}] 开始异动管线")
        runner = PipelineRunner("anomaly_v11", ANOMALY_V11_TASKS)
        await runner.run(biz_date, mode=mode)

        await alerter.alert("INFO", f"异动管线完成 {biz_date}", {
            "mode": mode,
        })
    except Exception as e:
        await alerter.alert("ERROR", f"管线整体失败 {biz_date}", {
            "error": str(e),
            "stack": traceback.format_exc()[:2000],
        })
        raise
```

### E5-S4 时间线

```
═══════════════════════════════════════════════════════
盘中(交易日 09:30-15:00)
═══════════════════════════════════════════════════════
内网 pytdx 持续采集 → 内网 CK
  ├ 5/15/30 分钟 K 线
  ├ 分时数据
  └ 实时盘口快照

═══════════════════════════════════════════════════════
云端时间线(数据采集)
═══════════════════════════════════════════════════════
15:30  daily_monitor_data_sync
17:00+ daily_kline_watcher (每30m)
17:30  daily_etf_kline_sync
19:00  daily_market_data_sync
19:20  daily_l2_structural_sync (仅采集 ODS)
19:40  daily_sentiment_sync
20:00  daily_financial_incremental_sync
20:30  云端采集任务全部完成
       └ readiness 表标记完成

═══════════════════════════════════════════════════════
内网时间线(计算与回写)
═══════════════════════════════════════════════════════
20:30+ anomaly_trigger_watcher 启动(每 1 分钟)
       └ 检测云端 readiness

20:35  云端就绪检测通过
       ├ Step 1: 同步云端 ODS → 内网 MySQL 副本(~3-5min)
       └ readiness 同步完成

20:40  L1/L2 因子计算开始(~5-8min)
       ├ 输入:CK(盘中聚合)+ 内网副本(日终)
       ├ 输出:写内网副本 + 双写云端
       └ 更新 readiness

20:48  异动管线启动(~10-12min)
       ├ Step 1: compute_derived_metrics
       ├ Step 2: compute_market_state
       ├ Step 3: produce_strong_pool
       ├ Step 4: compute_early_combo1
       ├ Step 5: compute_trap_signals
       ├ Step 6: compute_tags
       ├ Step 7: compute_score_composite
       └ Step 8: generate_top10

21:00  异动管线完成
       └ Top10 双写云端(~30s),前端可拉取

22:00  anomaly_deadline 死线兜底
23:30  daily_audit 日终自检
03:00  consistency_reconcile 一致性对账
═══════════════════════════════════════════════════════
```

### E5-S5 验收标准

- **Given** 交易日云端数据 20:30 全部就绪
- **When** 异动管线触发
- **Then** 21:00 前 `app_anomaly_top10_daily` 表当日数据写入云端,readiness 标记 READY

- **Given** 某 task 因 OOM 被子进程隔离杀死
- **When** PipelineRunner 检测到失败
- **Then** 自动重试 1 次;若仍失败,该 task 标记 FAILED,downstream task 中断;关键 task 失败发送 ERROR 告警

- **Given** L4 情绪数据某日采集失败(非关键)
- **When** 22:00 死线触发,critical 表全部就绪
- **Then** 管线以 `degraded` 模式运行,跳过依赖 L4 的可降级 task,产出标记 `data_completeness=partial` 的结果

---

## E6 · 邮件告警

### E6-S1 配置

```python
# config/alerter.py
ALERT_CONFIG = {
    "smtp_host": "smtp.qq.com",
    "smtp_port": 465,
    "smtp_user": "${SMTP_USER}",
    "smtp_pass": "${SMTP_PASS}",
    "from_addr": "${SMTP_USER}",
    "to_addrs": ["${ALERT_RECEIVER}"],
    "level_threshold": "WARN",         # 低于此级别不发邮件
    "dedup_window_sec": 300,            # 同告警 5 分钟内不重复
}
```

### E6-S2 实现

```python
# common/alerter.py
class Alerter:
    LEVELS = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3, "CRITICAL": 4}

    async def alert(self, level: str, title: str, context: dict = None):
        # 1. 始终写日志
        getattr(logger, level.lower(), logger.info)(f"{title} | {context}")

        # 2. 级别阈值过滤
        if self.LEVELS[level] < self.LEVELS[ALERT_CONFIG["level_threshold"]]:
            return

        # 3. 防抖
        dedup_key = f"alert:{level}:{title}:{hash(str(context))}"
        if await redis.exists(dedup_key):
            return
        await redis.setex(dedup_key, ALERT_CONFIG["dedup_window_sec"], "1")

        # 4. 发送
        await self._send_email(level, title, context)

    async def _send_email(self, level, title, context):
        subject = f"[{level}][stock-system] {title}"
        body = self._render_body(level, title, context)
        msg = build_email(
            from_addr=ALERT_CONFIG["from_addr"],
            to_addrs=ALERT_CONFIG["to_addrs"],
            subject=subject, body=body,
        )
        try:
            await aiosmtplib.send(
                message=msg,
                hostname=ALERT_CONFIG["smtp_host"],
                port=ALERT_CONFIG["smtp_port"],
                username=ALERT_CONFIG["smtp_user"],
                password=ALERT_CONFIG["smtp_pass"],
                use_tls=True,
                timeout=10,
            )
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            # 邮件失败不再告警(避免循环),只写本地文件
            with open("/var/log/alert_failed.log", "a") as f:
                f.write(f"{datetime.now()} {level} {title} {context}\n")
```

### E6-S3 告警分级矩阵

| 级别 | 触发场景 | 邮件 | 期望响应 |
|---|---|---|---|
| INFO | 任务成功、日历扩展、对账无异常 | 不发 | 不需要 |
| WARN | 单 task 重试、降级运行、数据延迟 > 30min、Tushare 额度 > 80%、隧道短暂断线 | 发 | 次日检查 |
| ERROR | 管线整体跳过、关键 task 终态失败、对账不一致、云端回写失败 | 发 | 当晚介入 |
| CRITICAL | 调度器无响应、连续 2 日异常、磁盘 > 90%、内网服务器宕机 | 发 | 立即处理 |

### E6-S4 系统资源自监控

```python
# stock_compute/scheduler/jobs/health_monitor.py
@scheduler.scheduled_job("interval", minutes=5, id="health_monitor")
async def system_health_check():
    # CPU
    cpu_pct = psutil.cpu_percent(interval=5)
    if cpu_pct > 90:
        await alerter.alert("WARN", "CPU 持续高负载", {"cpu_pct": cpu_pct})

    # 内存
    mem = psutil.virtual_memory()
    if mem.percent > 90:
        await alerter.alert("WARN", "内存压力高", {
            "percent": mem.percent,
            "available_mb": mem.available // 1024 // 1024,
        })

    # 磁盘
    disk = psutil.disk_usage("/")
    if disk.percent > 90:
        await alerter.alert("CRITICAL", "磁盘空间不足", {
            "percent": disk.percent,
            "free_gb": disk.free // 1024 // 1024 // 1024,
        })

    # SSH 隧道存活检查
    try:
        sock = socket.create_connection(("127.0.0.1", 13306), timeout=3)
        sock.close()
    except Exception:
        await alerter.alert("WARN", "SSH 隧道连接异常", {})
```

### E6-S5 日终自检

```python
@scheduler.scheduled_job("cron", hour=23, minute=30, id="daily_audit")
async def daily_audit():
    """日终自检,确认当日所有应跑任务完成情况"""
    biz_date = date.today()
    is_trading = await calendar_service.is_trading_day(biz_date)

    audit_items = [
        # (任务/管线 ID, 是否要求交易日, 校验函数)
        ("daily_market_overview_sync", True, check_l1_l2_complete),
        ("anomaly_v11", True, check_top10_complete),
        ("daily_finance_indicators_sync", False, check_finance_updated),
    ]

    failed = []
    for task_id, require_trading, validator in audit_items:
        if require_trading and not is_trading:
            continue
        try:
            ok = await validator(biz_date)
            if not ok:
                failed.append(task_id)
        except Exception as e:
            failed.append(f"{task_id}({e})")

    if failed:
        await alerter.alert("ERROR", "日终自检失败", {
            "biz_date": biz_date.isoformat(),
            "failed": failed,
        })
    else:
        logger.info(f"日终自检通过 {biz_date}")
```

---

## E7 · 部署与运维

### E7-S1 内网服务器部署

```yaml
# /opt/stock-compute/docker-compose.yml
version: '3.8'

services:
  internal-mysql:
    image: mysql:8.0
    container_name: internal-mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${INTERNAL_MYSQL_PASS}
      MYSQL_DATABASE: stock
    volumes:
      - ./mysql-data:/var/lib/mysql
      - ./mysql-conf/my.cnf:/etc/mysql/conf.d/custom.cnf:ro
    ports:
      - "127.0.0.1:3306:3306"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 30s
      timeout: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: redis
    command: redis-server --maxmemory 500mb --maxmemory-policy allkeys-lru
              --appendonly yes
    volumes:
      - ./redis-data:/data
    ports:
      - "127.0.0.1:6379:6379"
    restart: unless-stopped

  stock-compute:
    image: stock-compute:latest
    container_name: stock-compute
    depends_on:
      internal-mysql:
        condition: service_healthy
      redis:
        condition: service_started
    environment:
      INTERNAL_DB_URL: mysql+pymysql://root:${INTERNAL_MYSQL_PASS}@internal-mysql:3306/stock
      CLOUD_DB_URL: mysql+pymysql://compute:${CLOUD_DB_PASS}@host.docker.internal:13306/stock?compress=true
      CK_HOST: ${CK_HOST}
      CK_PORT: 9000
      CK_USER: ${CK_USER}
      CK_PASS: ${CK_PASS}
      REDIS_URL: redis://redis:6379/0
      SMTP_HOST: smtp.qq.com
      SMTP_USER: ${SMTP_USER}
      SMTP_PASS: ${SMTP_PASS}
      ALERT_RECEIVER: ${ALERT_RECEIVER}
      TZ: Asia/Shanghai
    volumes:
      - ./logs:/app/logs
      - ./scripts:/app/scripts:ro
      - ./sql:/app/sql:ro
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped
    mem_limit: 6g
```

### E7-S2 SSH 隧道守护

```ini
# /etc/systemd/system/mysql-tunnel.service
[Unit]
Description=MySQL SSH Tunnel to Cloud
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=tunnel
Environment="AUTOSSH_GATETIME=0"
ExecStart=/usr/bin/autossh -M 0 -N \
    -o "ServerAliveInterval=30" \
    -o "ServerAliveCountMax=3" \
    -o "ExitOnForwardFailure=yes" \
    -o "StrictHostKeyChecking=accept-new" \
    -i /home/tunnel/.ssh/id_rsa \
    -L 13306:127.0.0.1:3306 \
    tunnel@${CLOUD_HOST}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mysql-tunnel
sudo systemctl status mysql-tunnel
```

### E7-S3 内网 MySQL 配置

```ini
# /opt/stock-compute/mysql-conf/my.cnf
[mysqld]
# 资源充足,放开内存
innodb_buffer_pool_size = 4G
innodb_buffer_pool_instances = 4
innodb_log_file_size = 512M
innodb_log_buffer_size = 32M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

max_connections = 200
thread_cache_size = 32
table_open_cache = 4000
tmp_table_size = 128M
max_heap_table_size = 128M

slow_query_log = 1
long_query_time = 1

character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
default-time-zone = '+08:00'
```

### E7-S4 备份策略

```python
# stock_compute/scheduler/jobs/backup.py
@scheduler.scheduled_job("cron", hour=2, minute=30, id="daily_backup")
async def daily_backup():
    """每日 02:30 备份关键表(从云端 mysqldump)"""
    backup_dir = f"/backup/{date.today().isoformat()}"
    os.makedirs(backup_dir, exist_ok=True)

    CRITICAL_TABLES = [
        "ads_l1_market_overview",
        "ads_l2_structural",
        "ads_l8_unified_signal",
        "ads_anomaly_score",
        "app_anomaly_top10_daily",
        "meta_data_readiness",
        "meta_pipeline_run",
        "meta_trading_calendar",
    ]

    for table in CRITICAL_TABLES:
        cmd = [
            "mysqldump",
            "-h", "127.0.0.1", "-P", "13306",
            "-u", "backup_user", f"-p{BACKUP_PASS}",
            "--single-transaction",
            "--compress",
            "stock", table,
        ]
        out_file = f"{backup_dir}/{table}.sql.gz"
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE
        )
        # gzip 压缩
        with gzip.open(out_file, "wb") as f:
            async for chunk in proc.stdout:
                f.write(chunk)
        await proc.wait()

    # 保留 30 天
    cleanup_old_backups("/backup", days=30)
```

### E7-S5 监控指标暴露

```python
# stock_compute/api/dashboard.py
@app.get("/api/v1/dashboard")
async def get_dashboard():
    biz_date = date.today()
    return {
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "uptime_hours": (time.time() - psutil.boot_time()) / 3600,
        },
        "tunnel": {
            "alive": await check_tunnel_alive(),
            "last_disconnect": await get_last_disconnect_time(),
        },
        "database": {
            "internal_connections": await internal_db.fetch_val(
                "SELECT COUNT(*) FROM information_schema.PROCESSLIST"
            ),
            "cloud_connections": await cloud_db.fetch_val(
                "SELECT COUNT(*) FROM information_schema.PROCESSLIST"
            ),
        },
        "pipeline": {
            "anomaly_v11": await get_pipeline_status("anomaly_v11", biz_date),
            "l1_l2_compute": await get_pipeline_status("l1_l2", biz_date),
        },
        "data_readiness": await get_readiness_summary(biz_date),
    }
```

---

## E8 · 实施路径

### E8-S1 阶段一:止血(Week 1,2 天)

| Story | Task | 工作量 | 验收 |
|---|---|---|---|
| E1 实施 | 创建 `meta_trading_calendar` 表并初始化 | 0.5d | 表存在,有未来 3 年数据 |
| E1 实施 | 实现 `CalendarService` 与装饰器 | 0.5d | 单测通过 |
| E1 实施 | 现有任务全部接入装饰器(按 E1-S4 矩阵) | 0.5d | 周末非交易日日志干净 |
| E6 实施 | 邮件告警最小版接入 | 0.5d | 触发测试告警能收到 |

**完成后**:周末日志不再产生错误,出问题能收到邮件。

### E8-S2 阶段二:就绪契约 + 状态机(Week 2,3 天)

| Story | Task | 工作量 |
|---|---|---|
| E2 实施 | 云 MySQL 创建 `meta_data_readiness` 表 | 0.5d |
| E2 实施 | 云端 `readiness_prober` 旁路探测 | 0.5d |
| E3 实施 | 云 MySQL 创建 `meta_pipeline_run` 表 | 0.5d |
| E3 实施 | 实现 `PipelineRunner`(基础版,先支持 python/sql) | 1d |
| E3 实施 | 实现全局闸门(Redis 锁) | 0.5d |
| E6 实施 | 系统资源监控 + 告警接入 | 0.5d |

### E8-S3 阶段三:内网 MySQL 副本与同步(Week 3,2 天)

| Story | Task | 工作量 |
|---|---|---|
| 部署 | 内网 MySQL 部署(docker-compose) | 0.5d |
| 部署 | 副本数据库初始化(同云端表结构) | 0.5d |
| E4 实施 | `CloudDataSyncer` 实现 | 1d |
| E4 实施 | 一致性对账任务 | 0.5d |
| 验证 | 全量初始化拉取 90 天历史数据 | 0.5d (并行) |

### E8-S4 阶段四:计算迁移(Week 4,3 天)

| Story | Task | 工作量 |
|---|---|---|
| 迁移 | L1/L2 计算逻辑从云端迁移到内网 | 1.5d |
| 实施 | `DualWriter` 双写实现 | 0.5d |
| 验证 | 端到端跑通 1 天数据,与云端原计算结果对账 | 1d |
| 切换 | 禁用云端 stock-manager 中的计算任务 | — |

### E8-S5 阶段五:异动管线落地(Week 5,4 天)

| Story | Task | 工作量 |
|---|---|---|
| 实施 | 异动 8 个 task 编写 | 2d |
| 实施 | `anomaly_trigger_watcher` + `anomaly_deadline` | 0.5d |
| 实施 | python_isolated 子进程隔离执行 | 0.5d |
| 验证 | 端到端 dry-run + 灰度运行 1 周 | 1d (5d 并行) |

### E8-S6 总计

| 阶段 | 历时 | 工作量 |
|---|---|---|
| 阶段一 止血 | 1 周 | 2d |
| 阶段二 就绪契约 + 状态机 | 1 周 | 3d |
| 阶段三 内网 MySQL 副本 + 同步 | 1 周 | 2d |
| 阶段四 计算迁移 | 1 周 | 3d |
| 阶段五 异动管线 | 1 周 | 4d (+5d 灰度) |
| **合计** | **5-6 周** | **14 工作日** |

---

## E9 · 技术依赖

### E9-S1 软件依赖

| 组件 | 版本 | 用途 |
|---|---|---|
| Python | 3.10+ | 主语言 |
| APScheduler | 3.10+ | 调度框架 |
| SQLAlchemy | 2.0+ | ORM |
| aiomysql / pymysql | 最新稳定 | MySQL 客户端 |
| clickhouse-driver | 最新 | CK 客户端 |
| redis-py | 4.5+ | Redis + 分布式锁 |
| aiosmtplib | 最新 | 异步 SMTP |
| psutil | 最新 | 系统监控 |
| autossh | 系统包 | SSH 隧道守护 |
| Docker / Compose | 最新 | 容器化部署 |

### E9-S2 外部依赖

| 服务 | 用途 | 风险 |
|---|---|---|
| Tushare | 交易日历、机构评级、股东数据 | 5000 次/天额度 |
| AkShare | 行情、财务、情绪 | 无明确额度但有 IP 限频 |
| BaoStock | K 线兜底 | 长连接易断 |
| pytdx | 盘中数据 | 已稳定运行 |
| 腾讯企业邮箱 / QQ 邮箱 | SMTP 告警 | SMTP 偶发抖动 |

### E9-S3 资源占用预估

**内网服务器**(假设 8 核 16G):

| 任务 | 峰值 CPU | 峰值内存 | 持续时长 |
|---|---|---|---|
| 数据同步 | 1 核 | 500 MB | 3-5 min |
| L1/L2 计算 | 2-3 核 | 2 GB | 5-8 min |
| 异动管线 | 2-3 核 | 2 GB(子进程隔离) | 10-12 min |
| 内网 MySQL | 1-2 核 | 4 GB(buffer pool) | 持续 |
| 内网 CK | 1-2 核 | 已有占用 | 持续 |
| Redis | <0.5 核 | 500 MB | 持续 |

**总计峰值**:~6 核 / 9 GB,内网 8 核 16G 充足。

**云端 ECS**(2核4G):

| 任务 | 峰值占用 |
|---|---|
| 数据采集任务 | 错峰执行,单任务峰值 1 核 / 800MB |
| 调度器 + API | 持续 0.3 核 / 600MB |

总体压力较改造前**显著降低**(计算任务移走)。

---

## E10 · 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|---|---|---|---|
| SSH 隧道偶尔断线 | 中 | 中 | autossh 自动重连;计算任务连接重试 |
| 云 MySQL 1核1G 在采集高峰仍卡顿 | 中 | 低 | 任务错峰已缓解;内网承担读压力后只剩写 |
| 内网服务器宕机 | 低 | 高 | systemd 自动拉起;CRITICAL 告警 |
| pytdx 盘中数据缺失 | 中 | 高 | 异动管线检测 CK 完整性,缺失则相关 task 降级 |
| 跨网回写云端中断 | 中 | 中 | 双写设计:内网先写,云端补偿队列重试 |
| 业务方对 21:00 出结果延迟不满 | 低 | 中 | 已与业务确认接受;数据完整性优先 |
| Tushare 额度耗尽 | 低 | 中 | 调用前检查额度,> 90% 触发降级 |
| 内网 MySQL 副本数据漂移 | 低 | 中 | 凌晨 03:00 一致性对账,自动补齐 |
| 邮件告警 SMTP 抖动 | 中 | 低 | 失败写本地日志兜底 |

---

## E11 · 度量指标

| 指标 | 目标 | 告警阈值 |
|---|---|---|
| 异动管线交易日 SLA | 21:00 前完成 | 21:30 仍未完成 → ERROR |
| 管线连续成功天数 | ≥ 30 天 | 连续 2 日失败 → CRITICAL |
| 数据就绪 → 管线启动延迟 | < 10 分钟 | > 30 分钟 → WARN |
| L1/L2 计算耗时 | < 10 分钟 | > 15 分钟 → WARN |
| 异动管线总耗时 | < 15 分钟 | > 25 分钟 → WARN |
| 跨网同步耗时 | < 5 分钟 | > 10 分钟 → WARN |
| 双写一致性 | 100% | 任意不一致 → WARN |
| 隧道断线次数 | 日 < 1 次 | 日 ≥ 3 次 → WARN |
| 非交易日错误日志 | 0 条 | 任意 > 0 → 立即修复 |

---

## 不确定项 / TBD

- 异动管线 9 张表的具体 DDL 待补充(本文档已列清单,字段需要业务侧确认)
- L3 资金流和 L8 异动信号在现有云端任务中的具体产出位置 TBD,需要查代码确认
- 云端现有的 `daily_market_overview_sync` 内部步骤是否要全部迁移到内网 TBD,建议第一版保留云端版本,内网版本逐步替代
- pytdx 在 CK 中的具体表结构和保留策略 TBD,异动 task 编写时需要对齐
- 内网服务器具体规格 TBD,本方案按 8 核 16G+ 假设
- Redis 是否已部署 TBD,如未部署需要在阶段一前置完成
- 业务方对 21:00 出结果延迟的最终确认 TBD

---

## 变更记录

| 日期 | 版本 | 变更说明 | 作者 |
|---|---|---|---|
| 2026-05-03 | v1.0 | 初稿 | 架构组 |
| 2026-05-05 | v1.1 | 更新实施进度：基础底座 (E1, E2, E3, E6) 已完成交付 | Antigravity |
