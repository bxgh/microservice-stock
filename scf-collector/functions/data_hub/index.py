import sys
import os
import asyncio
import logging

# 为了能在云端正确引包，需要将共享目录加入 PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
# 自动寻找 shared 目录：优先检查同级目录（用于根目录部署），否则查找上两级目录（用于开发目录结构）
if os.path.exists(os.path.join(current_dir, 'shared')):
    shared_dir = current_dir
else:
    shared_dir = os.path.abspath(os.path.join(current_dir, '../../'))

if shared_dir not in sys.path:
    sys.path.insert(0, shared_dir)

from shared.collectors.tushare_cl import TushareCollector
from shared.collectors.akshare_cl import AkShareCollector
from shared.collectors.mootdx_cl import MootdxCollector
from shared.db.dao import StockDAO
from shared.utils.notifier import EmailNotifier

# 初始化日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 缓存采集器实例避免反复创建
COLLECTORS = {
    'tushare': TushareCollector(),
    'akshare': AkShareCollector(),
    'mootdx': MootdxCollector()
}

FALLBACK_CHAIN = ['tushare', 'mootdx', 'akshare']

async def async_handler(event, context):
    """
    异步处理逻辑 (集成存储与通知)
    """
    ts_code = event.get('ts_code')
    trade_date = event.get('trade_date')
    preferred_source = event.get('source', 'tushare')
    auto_fallback = event.get('auto_fallback', True)
    # SCF context 提供的 request_id 可作为任务流水 ID
    request_id = getattr(context, 'request_id', 'local_test')
    
    if not ts_code or not trade_date:
        return {"error": "Missing ts_code or trade_date"}
        
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
        # --- 数据持久化环节 ---
        try:
            # 1. 保存 K 线数据 (幂等)
            await StockDAO.save_kline_data(final_data)
            
            # 2. 记录审计流水
            await StockDAO.log_pipeline_run("Data-Hub", "success", run_id=request_id)
            
            # 3. 更新数据就绪状态
            await StockDAO.update_data_readiness(trade_date, used_src, len(final_data))
            
            # 4. 邮件通知 (异步)
            await EmailNotifier.notify_success("Data-Hub", trade_date, len(final_data))
            
            return {
                "status": "success",
                "source_used": used_src,
                "count": len(final_data),
                "request_id": request_id
            }
        except Exception as db_e:
            err_msg = f"Database/Notify error: {str(db_e)}"
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Data-Hub", "error", error_msg=err_msg, run_id=request_id)
            return {"status": "failed", "error": err_msg, "request_id": request_id}
    else:
        err_msg = "All sources failed."
        await StockDAO.log_pipeline_run("Data-Hub", "error", error_msg=err_msg, run_id=request_id)
        await EmailNotifier.notify_failure("Data-Hub", trade_date, err_msg)
        return {"status": "failed", "error": err_msg, "request_id": request_id}

def main_handler(event, context):
    return asyncio.run(async_handler(event, context))
