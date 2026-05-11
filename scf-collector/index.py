import sys
import os

# 0. 强制设置缓存路径 (解决 SCF 只读文件系统报错，必须在 import mootdx 之前)
os.environ['MOOTDX_CACHE_DIR'] = '/tmp'

import logging
import json
import asyncio

# 1. 强力路径搜索（确保 Layer 挂载被识别）
for path in ['/opt', '/opt/python', '/opt/python/lib/python3.10/site-packages']:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

# 2. 本地相对路径搜索
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 初始化日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 引入自定义模块
from shared.collectors.tushare_cl import TushareCollector
from shared.collectors.akshare_cl import AkShareCollector
from shared.collectors.mootdx_cl import MootdxCollector
from shared.db.dao import StockDAO
from shared.utils.notifier import EmailNotifier

# 缓存采集器实例
COLLECTORS = {
    'tushare': TushareCollector(),
    'akshare': AkShareCollector(),
    'mootdx': MootdxCollector()
}

FALLBACK_CHAIN = ['tushare', 'mootdx', 'akshare']

async def async_handler(event, context):
    ts_code = event.get('ts_code', '600519.SH')
    trade_date = event.get('trade_date', '20260511')
    preferred_source = event.get('source', 'tushare')
    auto_fallback = event.get('auto_fallback', True)
    request_id = getattr(context, 'request_id', 'local_test')
    
    logger.info(f">>> SCF Collector Heartbeat: Verification mode enabled. Request ID: {request_id} <<<")
    logger.info(f"[{request_id}] Start collecting {ts_code} for {trade_date}. Preferred: {preferred_source}")
    
    try_sources = [preferred_source]
    if auto_fallback:
        for s in FALLBACK_CHAIN:
            if s != preferred_source:
                try_sources.append(s)
                
    final_data = None
    used_src = None

    for src in try_sources:
        collector = COLLECTORS.get(src)
        if not collector: continue
            
        logger.info(f"[{request_id}] Trying source: {src}...")
        try:
            data = await collector.fetch_daily_kline(ts_code, trade_date)
            if data and len(data) > 0:
                final_data = data
                used_src = src
                break
            else:
                logger.warning(f"[{request_id}] Source {src} returned empty data.")
        except Exception as e:
            logger.error(f"[{request_id}] Source {src} exception: {str(e)}")

    if final_data:
        try:
            await StockDAO.save_kline_data(final_data)
            await StockDAO.log_pipeline_run("Data-Hub", "success", run_id=request_id, biz_date=trade_date)
            await StockDAO.update_data_readiness(trade_date, "stock_kline_daily", len(final_data))
            await EmailNotifier.notify_success("Data-Hub", trade_date, len(final_data))
            
            return {
                "status": "success",
                "source_used": used_src,
                "count": len(final_data),
                "request_id": request_id
            }
        except Exception as db_e:
            err_msg = f"Database error: {str(db_e)}"
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Data-Hub", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
            return {"status": "failed", "error": err_msg, "request_id": request_id}
    else:
        err_msg = "All sources failed ..."
        logger.error(f"[{request_id}] {err_msg}")
        await StockDAO.log_pipeline_run("Data-Hub", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
        return {"status": "failed", "error": err_msg, "request_id": request_id}

def main_handler(event, context):
    return asyncio.run(async_handler(event, context))
