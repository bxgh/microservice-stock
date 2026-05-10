import logging
import datetime
import psutil
import socket
from typing import Dict, Any
from app.utils.database import db
from app.utils.alerter import alerter
from app.common.scheduler_decorators import trading_day_only, notify_result

logger = logging.getLogger("stock-manager.system-jobs")

# 用于就绪状态缓存，避免重复查询数据库
_ready_cache = {}


async def system_health_monitor_job() -> Dict[str, Any]:
    """每 5 分钟执行一次系统健康检查"""
    try:
        # 1. CPU
        cpu_pct = psutil.cpu_percent(interval=1)
        if cpu_pct > 90:
            await alerter.alert("WARN", "CPU 负载过高", {"cpu_percent": cpu_pct})

        # 2. 内存
        mem = psutil.virtual_memory()
        if mem.percent > 90:
            await alerter.alert("WARN", "内存占用过高", {
                "percent": mem.percent,
                "available_mb": mem.available // 1024 // 1024
            })

        # 3. 磁盘
        disk = psutil.disk_usage("/")
        if disk.percent > 90:
            await alerter.alert("CRITICAL", "磁盘空间不足", {
                "percent": disk.percent,
                "free_gb": disk.free // 1024 // 1024 // 1024
            })

        return {"status": "success", "cpu": cpu_pct, "mem": mem.percent}
    except Exception as e:
        logger.error(f"健康检查任务异常: {e}")
        return {"status": "error", "message": str(e)}


@trading_day_only()
async def readiness_prober_job() -> Dict[str, Any]:
    """数据就绪状态探测器 (全生命周期感知)"""
    now = datetime.datetime.now()
    biz_date = datetime.date.today()
    biz_date_str = biz_date.isoformat()
    
    from app.services.workflow_service import workflow_service
    from app.services.pipeline_service import pipeline_service
    from app.services.market_data_service import MarketDataService
    market_service = MarketDataService()

    # --- 1. 晨间预就绪探测 (08:00 - 09:30) ---
    if datetime.time(8, 0) <= now.time() <= datetime.time(9, 30):
        # 检查 Morning Pipeline 是否已成功执行
        if not await pipeline_service.is_stage_success(workflow_service.PIPELINE_MORNING, biz_date_str, workflow_service.STAGE_M1):
            logger.debug(f"【探测】执行晨间就绪探测 (Morning Prep)")
            # 探测 Tushare 停复牌数据是否已投放今日数据 (作为晨间就绪的 Canary)
            is_ready = await market_service.sync_stock_suspend(suspend_date=biz_date_str)
            if is_ready > 0:
                logger.info(f"【探测】晨间数据源已就绪，启动 Phase I (Morning Prep)")
                asyncio.create_task(workflow_service.process_morning_trigger(biz_date))
                return {"status": "morning_triggered"}
            else:
                return {"status": "morning_pending"}

    # --- 2. 活跃窗口压制：仅在 19:00 - 23:00 期间执行高频探测 ---
    if not (datetime.time(19, 0) <= now.time() <= datetime.time(23, 0)):
        # 补充：下午收盘后的 Canary 探测 (15:30 - 19:00)
        if datetime.time(15, 30) <= now.time() <= datetime.time(19, 0):
             if not await pipeline_service.is_stage_success(workflow_service.PIPELINE_POST_MARKET, biz_date_str, workflow_service.STAGE_A):
                logger.debug(f"【探测】执行收盘后 Canary 探测 ({biz_date_str})")
                is_ready = await market_service.check_canary_ready(biz_date_str)
                if is_ready:
                    logger.info(f"【探测】Canary 就绪，触发 Stage A (基础采集)")
                    asyncio.create_task(workflow_service.execute_stage(workflow_service.STAGE_A, biz_date))
                    return {"status": "stage_a_triggered"}
        
        return {"status": "outside_active_window"}

    # --- 3. 晚间高频状态探测 (19:00 - 23:00) ---
    global _ready_cache
    if _ready_cache.get(biz_date_str) == "ALL_READY":
        return {"status": "all_ready_cached"}

    try:
        from app.utils.database import db

        # --- 动态校准逻辑 ---
        sql_total = "SELECT COUNT(*) FROM stock_basic_info WHERE list_status = 'L'"
        total_listed_rows = await db.execute(sql_total)
        total_listed = total_listed_rows[0][0] if total_listed_rows else 5000
        kline_min_threshold = int(total_listed * 0.95)
        # ------------------

        # 探测规则: (表名, 日期字段, 预期最小行数)
        PROBE_RULES = [
            ("stock_kline_daily", "trade_date", kline_min_threshold),
            ("ods_sw_index_daily", "trade_date", 30),
            ("ads_l1_market_overview", "trade_date", 1),
            ("ads_l2_industry_daily", "trade_date", 30),
        ]

        results = []
        all_ready = True
        for table, date_col, min_rows in PROBE_RULES:
            cache_key = f"{biz_date_str}_{table}"
            if _ready_cache.get(cache_key):
                results.append({"table": table, "status": "READY (cached)"})
                continue

            sql = f"SELECT COUNT(*) FROM {table} WHERE {date_col} = %s AND is_deleted = 0"
            rows = await db.execute(sql, (biz_date,))
            count = rows[0][0] if rows else 0
            status = "READY" if count >= min_rows else ("PARTIAL" if count > 0 else "PENDING")

            if status == "READY":
                _ready_cache[cache_key] = True
            else:
                all_ready = False

            upsert_sql = """
            INSERT INTO meta_data_readiness
            (table_name, biz_date, storage, record_count, expected_min, producer_node, ready_at, status)
            VALUES (%s, %s, 'cloud_mysql', %s, %s, 'cloud', NOW(), %s)
            ON DUPLICATE KEY UPDATE
                record_count=VALUES(record_count), ready_at=VALUES(ready_at), status=VALUES(status)
            """
            await db.execute(upsert_sql, (table, biz_date, count, min_rows, status))
            results.append({"table": table, "status": status, "count": count})

        # 触发 WorkflowManager
        ready_tables = [r["table"] for r in results if "READY" in r["status"]]
        if ready_tables:
            asyncio.create_task(workflow_service.process_event(biz_date, ready_tables))

        if all_ready:
            _ready_cache[biz_date_str] = "ALL_READY"
            logger.info(f"【探测器】当日所有核心数据已就绪: {biz_date_str}")

        return {"status": "success", "探测详情": results, "ready_tables": ready_tables}

    except Exception as e:
        logger.error(f"就绪探测器致命异常: {e}")
        return {"status": "error", "message": str(e)}


@notify_result
@trading_day_only()
async def daily_audit_job() -> Dict[str, Any]:
    """日终审计任务 (23:30)"""
    biz_date = datetime.date.today()

    # 检查核心数据是否全部就绪
    try:
        sql = "SELECT table_name, status FROM meta_data_readiness WHERE biz_date = %s AND is_deleted = 0"
        rows = await db.execute(sql, (biz_date,))

        status_map = {row[0]: row[1] for row in rows}
        missing = []

        # 核心表清单
        CORE_TABLES = ["stock_kline_daily", "ads_l1_market_overview"]
        for table in CORE_TABLES:
            if status_map.get(table) != "READY":
                missing.append(table)

        if missing:
            await alerter.alert("ERROR", "当日核心数据未就绪", {
                "biz_date": biz_date.isoformat(),
                "missing_tables": ", ".join(missing)
            })
            return {"status": "failed", "missing": missing}

        return {"status": "success", "message": "所有核心数据已就绪"}
    except Exception as e:
        logger.error(f"日终审计异常: {e}")
        return {"status": "error", "message": str(e)}


async def backfill_enqueue_job():
    """补数扫描任务：每小时扫描一次 DQ 问题并入队"""
    from app.services.backfill_service import backfill_service
    try:
        await backfill_service.enqueue_findings()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"补数入队任务异常: {e}")
        return {"status": "error", "message": str(e)}


async def backfill_processor_job():
    """补数执行任务：每 5 分钟消费一次补数队列"""
    from app.services.backfill_service import backfill_service
    try:
        await backfill_service.process_queue(batch_size=10)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"补数执行任务异常: {e}")
        return {"status": "error", "message": str(e)}


@notify_result
@trading_day_only()
async def daily_dq_report_job() -> Dict[str, Any]:
    """每日数据质量报告任务 (09:05)
    目标表: meta_dq_metrics
    功能描述: 计算并统计 T-1 日全量数据的质量指标（空值率、对齐度等），并发送质量摘要邮件。
    """
    from app.services.dq_metrics_service import dq_metrics_service

    # 获取最近一个交易日
    try:
        sql = "SELECT cal_date FROM trade_cal WHERE cal_date < CURDATE() AND is_open = 1 ORDER BY cal_date DESC LIMIT 1"
        res = await db.execute(sql)
        if not res:
            return {"status": "skipped", "reason": "no_trading_day_found"}

        target_date = res[0][0]
        if isinstance(target_date, (datetime.date, datetime.datetime)):
            target_date = target_date.strftime("%Y-%m-%d")

        # 1. 计算指标
        metrics = await dq_metrics_service.calculate_daily_metrics(target_date)

        # 2. 发送告警 (如果指标显著低于预期)
        critical_issues = {k: v for k, v in metrics.items() if v < 0.90}
        if critical_issues:
            await alerter.alert("ERROR", f"DQ 指标严重偏离目标 ({target_date})", {
                "date": target_date,
                **critical_issues
            })
        elif any(v < 0.99 for v in metrics.values()):
            await alerter.alert("INFO", f"每日 DQ 质量报告 ({target_date})", {
                "date": target_date,
                **metrics
            })

        return {"status": "success", "日期": target_date, "质量指标": metrics}
    except Exception as e:
        logger.error(f"DQ 报告任务异常: {e}")
        return {"status": "error", "message": f"计算失败: {str(e)}"}


@notify_result
@trading_day_only()
async def safety_workflow_scan_job() -> Dict[str, Any]:
    """流水线保底扫描任务 (23:00)
    目标表: meta_pipeline_run
    功能描述: 扫描当日所有 READY 状态的数据表，强制驱动一次状态机流转，防止因事件丢失导致的管线中断。
    """
    biz_date = datetime.date.today()
    try:
        # 查询当日所有 READY 的表
        sql = "SELECT table_name FROM meta_data_readiness WHERE biz_date = %s AND status = 'READY' AND is_deleted = 0"
        rows = await db.execute(sql, (biz_date,))
        ready_tables = [row[0] for row in rows]
        
        if not ready_tables:
            return {"status": "skipped", "reason": "no_ready_tables_found"}
            
        from app.services.workflow_service import workflow_service
        # 同步调用（await），确保在 Job 结束前流水线触发逻辑已走完
        await workflow_service.process_event(biz_date, ready_tables)
        
        return {
            "status": "success", 
            "biz_date": biz_date.isoformat(),
            "ready_tables_count": len(ready_tables)
        }
    except Exception as e:
        logger.error(f"【保底扫描】执行异常: {e}")
        return {"status": "error", "message": str(e)}


@notify_result
async def daily_pipeline_summary_job() -> Dict[str, Any]:
    """每日数据管线执行总结报告 (23:45)
    目标表: meta_pipeline_run
    功能描述: 汇总当日所有流水线阶段的执行状态、耗时、异常详情，并发送 HTML 标准化报表邮件。
    """
    biz_date = datetime.date.today()
    from app.services.workflow_service import workflow_service
    try:
        await workflow_service.send_daily_summary_report(biz_date)
        return {"status": "success", "date": biz_date.isoformat()}
    except Exception as e:
        logger.error(f"【总结报告】执行异常: {e}")
        return {"status": "error", "message": str(e)}
