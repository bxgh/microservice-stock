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
        return {"status": "success", "count": count, "request_id": request_id}
    if op == 'validate_and_failover':
        # 17:00 完整性校验与熔断编排
        logger.info(f"[{request_id}] Starting integrity validation & fail-over for {trade_date}...")
        
        # 1. 加载基准
        snapshot = await StockDAO.get_universe_snapshot(trade_date)
        if not snapshot:
            logger.warning(f"[{request_id}] No baseline snapshot found for {trade_date}. Skipping validation.")
            return {"status": "skipped", "reason": "no_snapshot"}
        
        expected_n = snapshot['expected_count']
        
        # 2. 检查当前已入库量
        current_data = await StockDAO.get_kline_daily(trade_date)
        current_n = len(current_data)
        coverage = current_n / expected_n if expected_n > 0 else 0
        
        logger.info(f"[{request_id}] Initial check: Expected={expected_n}, Actual={current_n}, Coverage={coverage:.2%}")
        
        # 3. 判定与补救逻辑
        source_tag = "TUSHARE_P0"
        
        # 如果覆盖率不足 98%，触发重试或熔断
        if coverage < 0.98:
            if coverage < 0.95:
                logger.warning(f"[{request_id}] Critical coverage gap detected (<95%).")
            else:
                logger.info(f"[{request_id}] Warning coverage gap detected (<98%).")
                
            # A. 原位重试一次 Tushare
            logger.info(f"[{request_id}] Attempting Tushare in-place retry...")
            collector_ts = COLLECTORS.get('tushare')
            try:
                retry_data = await collector_ts.fetch_batch_daily_kline(trade_date)
                if retry_data and len(retry_data) > current_n:
                    await StockDAO.save_kline_data(retry_data)
                    current_data = await StockDAO.get_kline_daily(trade_date)
                    current_n = len(current_data)
                    coverage = current_n / expected_n
                    logger.info(f"[{request_id}] Retry success. New count: {current_n}, Coverage: {coverage:.2%}")
            except Exception as e:
                logger.error(f"[{request_id}] Tushare retry failed: {e}")

            # B. 最终裁定：若重试后仍不足 95%，执行全量接管
            if coverage < 0.95:
                logger.critical(f"[{request_id}] FAIL-OVER TRIGGERED: Switching to AkShare.")
                collector_ak = COLLECTORS.get('akshare')
                try:
                    # 使用全量快照补齐
                    import akshare as ak
                    df_ak = await asyncio.to_thread(ak.stock_zh_a_spot_em)
                    from shared.collectors.akshare_adapter import AkShareAdapter
                    final_ak_models = AkShareAdapter.from_em_spot_records(df_ak.to_dict(orient='records'), trade_date)
                    
                    if final_ak_models:
                        await StockDAO.save_kline_data(final_ak_models)
                        source_tag = "AKSHARE_P1_FAILOVER"
                        logger.info(f"[{request_id}] Fail-over successful. Records saved from AkShare.")
                        await EmailNotifier.notify_failure("Tushare完整性熔断", trade_date, f"已自动切换至AkShare补救。覆盖率:{coverage:.2%}")
                except Exception as e:
                    logger.error(f"[{request_id}] Fail-over execution error: {e}")
                    await EmailNotifier.notify_failure("数据采集全面失效", trade_date, f"主备源均无法满足完整性要求。{str(e)}")

        # 4. 运行影子审计并同步 source_tag
        from shared.utils.shadow_auditor import ShadowAuditor
        auditor = ShadowAuditor()
        audit_res = await auditor.run_audit(trade_date)
        
        # 覆盖审计日志中的 source_tag
        audit_res['source_tag'] = source_tag
        await StockDAO.save_audit_log(audit_res)
        
        # 5. 更新就绪状态
        # 只要审计判定为 PASS 或 WARNING (非 FAIL)，且已完成补救，则更新信号
        if audit_res['status'] in ['PASS', 'WARNING']:
            await StockDAO.update_data_readiness(trade_date, "stock_kline_daily", current_n)
            
        return {
            "status": "completed",
            "coverage": coverage,
            "source_tag": source_tag,
            "audit_status": audit_res['status'],
            "request_id": request_id
        }

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
