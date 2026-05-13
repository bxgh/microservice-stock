import sys
import os

# 0. 强制重定向环境路径 (解决 SCF 只读文件系统报错)
# 必须在 import 任何第三方行情库之前设置
os.environ['HOME'] = '/tmp'

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

# 强制从当前目录加载 .env (优先于本地环境变量)
from dotenv import load_dotenv
load_dotenv(os.path.join(current_dir, '.env'), override=True)

# 初始化日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 引入自定义模块
from shared.collectors.tushare_cl import TushareCollector
from shared.collectors.akshare_cl import AkShareCollector
from shared.collectors.easyquotation_cl import EasyQuotationCollector
from shared.db.dao import StockDAO
from shared.utils.notifier import EmailNotifier
from shared.utils.shadow_auditor import ShadowAuditor
import datetime
import uuid

# 缓存采集器实例
try:
    COLLECTORS = {
        'tushare': TushareCollector(),
        'akshare': AkShareCollector(),
        'easyquotation': EasyQuotationCollector()
    }
except Exception as e:
    logger.error(f"Critical: Failed to initialize collectors: {e}")
    COLLECTORS = {}

FALLBACK_CHAIN = ['tushare', 'akshare', 'easyquotation']

async def async_handler(event, context):
    logger.info(f"Received event: {event}")
    # 1. 尝试从 Message 字段解包 (Timer Trigger 专用)
    if 'Message' in event:
        try:
            msg_data = json.loads(event['Message'])
            if isinstance(msg_data, dict):
                event.update(msg_data)
        except Exception as e:
            logger.warning(f"Failed to parse Message field: {e}")

    op = event.get('op', 'collect')
    ts_code = event.get('ts_code', '600519.SH')
    # 如果没传日期，默认为当天
    trade_date = event.get('trade_date', datetime.datetime.now().strftime('%Y-%m-%d'))
    request_id = getattr(context, 'request_id', 'local_test')

    if op == 'verify':
        logger.info(f"[{request_id}] Entering Cloud Verification Mode...")
        results = {}
        for name, collector in COLLECTORS.items():
            try:
                # 统一测试 茅台 2026-05-11
                data = await collector.fetch_daily_kline(ts_code, trade_date)
                if data and len(data) > 0:
                    results[name] = f"SUCCESS ({data[0]['close']})"
                else:
                    results[name] = "FAILED (Empty)"
            except Exception as e:
                results[name] = f"ERROR ({str(e)})"
        return {"status": "verify_result", "data": results, "request_id": request_id}

    if op == 'migrate':
        logger.info(f"[{request_id}] Entering Cloud Source Inspection Mode (Disabled)...")
        return {"status": "success", "message": "Migration mode disabled for production"}

    if op == 'shadow_audit':
        # 执行影子审计：对比主源与备份源
        logger.info(f"[{request_id}] Starting shadow audit mission for {trade_date}...")
        auditor = ShadowAuditor()
        try:
            result = await auditor.run_audit(trade_date)
            overlap = result.get('overlap_count', 0)
            # 使用静态方法（与其他分支一致）
            await EmailNotifier.notify_success("数据源影子审计", trade_date, overlap, table_name="meta_data_audit_log")
            return {"status": "success", "audit": result, "request_id": request_id}
        except Exception as e:
            logger.error(f"Shadow audit failed: {e}")
            await EmailNotifier.notify_failure("数据源影子审计", trade_date, str(e))
            return {"status": "error", "message": str(e), "request_id": request_id}

    if op == 'sync_kline_daily':
        # 批量同步全 A 日 K 线 (不复权)
        logger.info(f"[{request_id}] Starting batch K-line sync for {trade_date}...")
        collector = COLLECTORS.get('tushare')
        try:
            data = await collector.fetch_batch_daily_kline(trade_date)
            if data:
                count = await StockDAO.save_kline_data(data)
                await StockDAO.update_data_readiness(trade_date, "stock_kline_daily", len(data))
                await StockDAO.log_pipeline_run("Daily-K-Line", "success", run_id=request_id, biz_date=trade_date)
                
                # 发送成功邮件 (增加表名)
                await EmailNotifier.notify_success("日K线批量采集", trade_date, count, table_name="stock_kline_daily")
                
                return {"status": "success", "count": count, "request_id": request_id}
            else:
                msg = "Tushare returned empty data (possibly non-trading day)."
                logger.info(f"[{request_id}] {msg}")
                return {"status": "empty", "count": 0, "request_id": request_id}
        except Exception as e:
            err_msg = f"Batch K-line sync error: {str(e)}"
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Daily-K-Line", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
            
            # 发送失败邮件
            await EmailNotifier.notify_failure("日K线批量采集", trade_date, err_msg)
            
            return {"status": "error", "message": err_msg, "request_id": request_id}

    if op == 'sync_adj_factor':
        # 批量同步复权因子
        logger.info(f"[{request_id}] Starting batch adj factor sync for {trade_date}...")
        collector = COLLECTORS.get('tushare')
        try:
            data = await collector.fetch_adj_factor(trade_date)
            if data:
                count = await StockDAO.save_adj_factor(data)
                await StockDAO.update_data_readiness(trade_date, "stock_adjust_factor", len(data))
                await StockDAO.log_pipeline_run("Adj-Factor", "success", run_id=request_id, biz_date=trade_date)
                
                # 发送成功邮件 (增加表名)
                await EmailNotifier.notify_success("复权因子批量采集", trade_date, count, table_name="stock_adjust_factor")
                
                return {"status": "success", "count": count, "request_id": request_id}
            else:
                return {"status": "empty", "count": 0, "request_id": request_id}
        except Exception as e:
            err_msg = f"Batch adj factor sync error: {str(e)}"
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Adj-Factor", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
            
            # 发送失败邮件
            await EmailNotifier.notify_failure("复权因子批量采集", trade_date, err_msg)
            
            return {"status": "error", "message": err_msg, "request_id": request_id}

    if op == 'sync_index_daily':
        # 批量同步指定指数行情
        ts_codes = event.get('ts_codes', '000001.SH,399001.SZ,399006.SZ,000300.SH,000905.SH,000852.SH,985.SH')
        logger.info(f"[{request_id}] Starting index sync for {trade_date}, codes: {ts_codes}...")
        collector = COLLECTORS.get('tushare')
        all_data = []
        for code in ts_codes.split(','):
            try:
                data = await collector.fetch_index_daily(code.strip(), trade_date)
                all_data.extend(data)
            except Exception as e:
                logger.error(f"[{request_id}] Error fetching index {code}: {e}")
        
        if all_data:
            count = await StockDAO.save_index_kline(all_data)
            await StockDAO.update_data_readiness(trade_date, "ods_index_daily", len(all_data))
            await StockDAO.log_pipeline_run("Index-Daily", "success", run_id=request_id, biz_date=trade_date)
            
            # 发送成功邮件
            await EmailNotifier.notify_success("指数K线同步", trade_date, count, table_name="ods_index_daily")
            
            return {"status": "success", "count": count, "request_id": request_id}
        return {"status": "empty", "request_id": request_id}

    try:
        preferred_source = event.get('source', 'tushare')
        auto_fallback = event.get('auto_fallback', True)
        
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
                await StockDAO.update_data_readiness(trade_date, "stock_kline_daily", len(final_data))
                await StockDAO.log_pipeline_run("Data-Hub", "success", run_id=request_id, biz_date=trade_date)
                
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
            err_msg = "All sources failed to fetch data."
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Data-Hub", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
            return {"status": "failed", "error": err_msg, "request_id": request_id}
    finally:
        # 核心修复：显式关闭连接池，防止 RuntimeError
        from shared.db.connection import DBManager
        await DBManager.close_pool()

def main_handler(event, context):
    return asyncio.run(async_handler(event, context))
