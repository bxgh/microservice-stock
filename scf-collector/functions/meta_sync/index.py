import sys
import os
import uuid
import logging
import json
import asyncio
import datetime
from datetime import timedelta

# 0. 强制重定向环境路径 (解决 SCF 只读文件系统报错)
os.environ['HOME'] = '/tmp'

# 1. 强力路径搜索（确保 Layer 挂载被识别）
for path in ['/opt', '/opt/python', '/opt/python/lib/python3.10/site-packages']:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

# 2. 本地相对路径搜索
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 强制从当前目录加载 .env
from dotenv import load_dotenv
load_dotenv(os.path.join(current_dir, '.env'), override=True)

# 初始化日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 引入自定义模块
from shared.collectors.tushare_cl import TushareCollector
from shared.db.dao import StockDAO
from shared.utils.trading_day import TradingDayGuard

# 缓存采集器实例
TUSHARE = TushareCollector()

async def async_handler(event, context):
    # 增强日志：打印原始 event 以便排查
    logger.info(f"Raw event received: {json.dumps(event, ensure_ascii=False)}")
    
    # 1. 尝试从 Message 字段解包 (Timer Trigger 专用)
    if 'Message' in event:
        try:
            msg_data = json.loads(event['Message'])
            if isinstance(msg_data, dict):
                # 将解包后的参数合并回 event，确保后续业务逻辑透明
                event.update(msg_data)
                logger.info(f"Unpacked parameters from Message: {json.dumps(msg_data)}")
        except Exception as e:
            logger.warning(f"Failed to parse Message field: {e}")

    # 2. 现在可以安全地从 event 中获取参数了
    op = event.get('op')
    if not op:
        op = 'unknown'
        
    request_id = getattr(context, 'request_id', str(uuid.uuid4()))
    biz_date = event.get('biz_date', datetime.datetime.now().strftime('%Y-%m-%d'))
    
    # [E7-S5-T3] 交易日准入校验
    if await TradingDayGuard.should_skip(op, biz_date):
        return {
            "status": "skipped", 
            "reason": "not_a_trading_day", 
            "op": op, 
            "biz_date": biz_date,
            "request_id": request_id
        }

    logger.info(f"[{request_id}] Final resolved task: {op} for {biz_date}")
    
    try:
        if op == 'sync_calendar':
            # 同步前后 1 年的日历，确保覆盖度
            start_date = (datetime.datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            end_date = (datetime.datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
            
            logger.info(f"[{request_id}] Fetching calendar from {start_date} to {end_date}...")
            data = await TUSHARE.fetch_trading_calendar(start_date, end_date)
            
            if data:
                count = await StockDAO.save_trading_calendar(data)
                await StockDAO.log_pipeline_run("Meta-Calendar", "success", run_id=request_id, biz_date=biz_date)
                # 交易日历通常不作为下游 Trigger 的唯一标准，但我们可以记录就绪
                await StockDAO.update_data_readiness(biz_date, "trade_cal", len(data))
                return {"status": "success", "op": op, "count": count, "request_id": request_id}
            else:
                raise Exception("Fetched empty calendar data")

        elif op == 'sync_stock_list':
            logger.info(f"[{request_id}] Fetching full stock list...")
            data = await TUSHARE.fetch_stock_list()
            
            if data:
                count = await StockDAO.save_stock_list(data)
                await StockDAO.log_pipeline_run("Meta-StockList", "success", run_id=request_id, biz_date=biz_date)
                await StockDAO.update_data_readiness(biz_date, "stock_basic_info", len(data))
                return {"status": "success", "op": op, "count": count, "request_id": request_id}
            else:
                raise Exception("Fetched empty stock list data")
        
        elif op == 'sync_sw_industry_member':
            logger.info(f"[{request_id}] Fetching SW industry members...")
            data = await TUSHARE.fetch_sw_industry_members()
            
            if data:
                count = await StockDAO.save_industry_members(data)
                await StockDAO.log_pipeline_run("Meta-Industry", "success", run_id=request_id, biz_date=biz_date)
                await StockDAO.update_data_readiness(biz_date, "dim_sw_industry_member", len(data))
                return {"status": "success", "op": op, "count": count, "request_id": request_id}
            else:
                raise Exception("Fetched empty SW industry members data")

        elif op == 'sync_suspension':
            logger.info(f"[{request_id}] Fetching daily suspensions for {biz_date}...")
            data = await TUSHARE.fetch_suspensions(biz_date)
            count = await StockDAO.save_suspensions(data)
            await StockDAO.log_pipeline_run("Meta-Suspension", "success", run_id=request_id, biz_date=biz_date)
            await StockDAO.update_data_readiness(biz_date, "ods_suspend_d", len(data))
            return {"status": "success", "op": op, "count": count, "request_id": request_id}

        elif op == 'create_universe_snapshot':
            logger.info(f"[{request_id}] Creating universe snapshot for {biz_date} (09:30 Task)...")
            
            # A. [Infra Specialist] 增强：停牌采集增加异常隔离，失败不阻断快照生成
            try:
                sus_data = await TUSHARE.fetch_suspensions(biz_date)
                await StockDAO.save_suspensions(sus_data)
                logger.info(f"[{request_id}] Suspension sync success: {len(sus_data)} records.")
            except Exception as e:
                logger.warning(f"[{request_id}] Suspension sync failed, fallback to 0: {e}")
            
            # B. 计算基准 (N = 上市总数 - 当日停牌)
            all_active = await StockDAO.get_active_stock_codes(biz_date)
            suspended = await StockDAO.get_suspended_codes(biz_date)
            
            # 逻辑对冲：计算真正应采的代码集合
            universe_set = set(all_active) - set(suspended)
            expected_count = len(universe_set)
            
            # C. 持久化快照
            await StockDAO.save_universe_snapshot(biz_date, expected_count, list(universe_set))
            
            logger.info(f"[{request_id}] Universe locked: Expected={expected_count} (Total={len(all_active)}, Suspended={len(suspended)})")
            
            await StockDAO.log_pipeline_run("Meta-Snapshot", "success", run_id=request_id, biz_date=biz_date)
            await StockDAO.update_data_readiness(biz_date, "meta_universe_snapshot", expected_count)
            
            return {
                "status": "success", 
                "op": op, 
                "expected_count": expected_count, 
                "suspended_count": len(suspended),
                "request_id": request_id
            }
        
        else:
            return {"status": "error", "message": f"Unknown operation: {op}", "request_id": request_id}

    except Exception as e:
        err_msg = f"Meta Sync Error ({op}): {str(e)}"
        logger.error(f"[{request_id}] {err_msg}")
        await StockDAO.log_pipeline_run(f"Meta-{op}", "error", error_message=err_msg, run_id=request_id, biz_date=biz_date)
        return {"status": "failed", "error": err_msg, "request_id": request_id}
    finally:
        # 核心修复：显式关闭连接池，防止 SCF 退出时 Event Loop 已关闭导致的 RuntimeError
        from shared.db.connection import DBManager
        await DBManager.close_pool()

def main_handler(event, context):
    return asyncio.run(async_handler(event, context))

if __name__ == "__main__":
    # 本地测试逻辑
    test_event = {"op": "sync_calendar"}
    print(main_handler(test_event, None))
