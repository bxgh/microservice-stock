import logging
import datetime
import psutil
import socket
from typing import Dict, Any
from app.utils.database import db
from app.utils.alerter import alerter
from app.common.scheduler_decorators import trading_day_only

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
    """数据就绪状态探测器 (带压制逻辑)"""
    now = datetime.datetime.now()
    
    # 1. 活跃窗口压制：仅在 19:00 - 23:00 期间执行高频探测
    if not (datetime.time(19, 0) <= now.time() <= datetime.time(23, 0)):
        return {"status": "outside_window"}
    
    biz_date = datetime.date.today()
    biz_date_str = biz_date.isoformat()
    
    # 2. 内存缓存压制：如果当日已标记为 ALL_READY，则不再查询数据库
    global _ready_cache
    if _ready_cache.get(biz_date_str) == "ALL_READY":
        return {"status": "all_ready_cached"}

    try:
        from app.utils.database import db
        
        # --- 动态校准逻辑 ---
        # 获取当前在市股票总数作为基准
        sql_total = "SELECT COUNT(*) FROM stock_basic_info WHERE list_status = 'L'"
        total_listed_rows = await db.execute(sql_total)
        total_listed = total_listed_rows[0][0] if total_listed_rows else 5000 # 兜底值
        
        # 设定 K 线预期最小行数为上市总数的 98%
        kline_min_threshold = int(total_listed * 0.98)
        logger.debug(f"【动态校准】当日上市股票总数: {total_listed}, K线就绪阈值设定为: {kline_min_threshold}")
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
            try:
                # 如果缓存中该表当日已就绪，跳过查询
                cache_key = f"{biz_date_str}_{table}"
                if _ready_cache.get(cache_key):
                    results.append({"table": table, "status": "READY (cached)"})
                    continue

                sql = f"SELECT COUNT(*) FROM {table} WHERE {date_col} = %s"
                rows = await db.execute(sql, (biz_date,))
                count = rows[0][0] if rows else 0
                
                status = "READY" if count >= min_rows else ("PARTIAL" if count > 0 else "PENDING")
                
                if status == "READY":
                    _ready_cache[cache_key] = True
                else:
                    all_ready = False

                # 写入 readiness 表
                upsert_sql = """
                INSERT INTO meta_data_readiness 
                (table_name, biz_date, storage, record_count, expected_min, producer_node, ready_at, status)
                VALUES (%s, %s, 'cloud_mysql', %s, %s, 'cloud', NOW(), %s)
                ON DUPLICATE KEY UPDATE 
                    record_count=VALUES(record_count),
                    ready_at=VALUES(ready_at),
                    status=VALUES(status)
                """
                await db.execute(upsert_sql, (table, biz_date, count, min_rows, status))
                results.append({"table": table, "status": status, "count": count})
                
            except Exception as e:
                all_ready = False
                logger.error(f"探测表 {table} 失败: {e}")
                
        if all_ready:
            _ready_cache[biz_date_str] = "ALL_READY"
            logger.info(f"【探测器】当日所有核心数据已就绪: {biz_date_str}")

        return {"status": "success", "details": results}

    except Exception as e:
        logger.error(f"就绪探测器致命异常: {e}")
        return {"status": "error", "message": str(e)}

@trading_day_only()
async def daily_audit_job() -> Dict[str, Any]:
    """日终审计任务 (23:30)"""
    biz_date = datetime.date.today()
        
    # 检查核心数据是否全部就绪
    try:
        sql = "SELECT table_name, status FROM meta_data_readiness WHERE biz_date = %s"
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
            
        return {"status": "success", "message": "All core data ready"}
    except Exception as e:
        logger.error(f"日终审计异常: {e}")
        return {"status": "error", "message": str(e)}
