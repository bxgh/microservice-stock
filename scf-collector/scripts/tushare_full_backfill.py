import os
import sys
import asyncio
import logging
import time
import datetime
from typing import List, Dict, Any

# 1. 路径修复：确保能从 scf-collector/shared 加载模块
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(root_dir, ".env"), override=True)

from shared.collectors.tushare_cl import TushareCollector
from shared.db.dao import StockDAO
from shared.db.connection import DBManager, execute_query

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(root_dir, 'logs', 'tushare_backfill.log'))
    ]
)
logger = logging.getLogger("TushareBackfill")

# Tushare 2000 积分策略：daily 接口 500次/min
# 我们设置保守的 1.2s 间隔，确保绝对不触发限流，同时保持单线程稳定
THROTTLE_SLEEP = 1.2
TASK_NAME = 'full_market_backfill'

async def get_trading_days() -> List[str]:
    """从数据库获取所有 A 股交易日"""
    sql = "SELECT cal_date FROM trade_cal WHERE is_open=1 AND exchange='SSE' ORDER BY cal_date ASC"
    rows = await execute_query(sql, is_select=True)
    days = []
    for r in rows:
        d = r['cal_date']
        if isinstance(d, datetime.date):
            days.append(d.strftime('%Y%m%d'))
        else:
            days.append(str(d).replace('-', ''))
    return days

async def save_batch_fast(data: List[Any]) -> int:
    """[Backend Engineer] 优化版批量保存：使用 executemany 提高回填效率"""
    if not data:
        return 0
        
    sql = """
    INSERT INTO stock_kline_daily (
        ts_code, trade_date, open, high, low, close, 
        pre_close, pct_chg, volume, amount
    ) VALUES (
        %(ts_code)s, %(trade_date)s, %(open)s, %(high)s, %(low)s, %(close)s, 
        %(pre_close)s, %(pct_chg)s, %(volume)s, %(amount)s
    ) ON DUPLICATE KEY UPDATE 
        open = VALUES(open), high = VALUES(high), low = VALUES(low), close = VALUES(close), 
        pre_close = VALUES(pre_close), pct_chg = VALUES(pct_chg), volume = VALUES(volume), amount = VALUES(amount)
    """
    
    pool = await DBManager.get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # 准备参数
            params = [item.model_dump() if hasattr(item, 'model_dump') else item for item in data]
            await cur.executemany(sql, params)
            return cur.rowcount

async def run_backfill():
    """主回填逻辑"""
    logger.info(">>> 启动 Tushare 全量回填引擎 (E13-S2-T1) <<<")
    
    collector = TushareCollector()
    if not collector.pro:
        logger.error("TUSHARE_TOKEN 未配置，任务终止")
        return

    # 1. 获取目标日期列表
    all_days = await get_trading_days()
    total_days = len(all_days)
    logger.info(f"待处理交易日总数: {total_days}")

    # 2. 循环执行
    for idx, day in enumerate(all_days):
        # [E13-S2-T2] 断点检查
        check_sql = "SELECT status FROM sync_progress WHERE task_name=%s AND current_code=%s"
        res = await execute_query(check_sql, (TASK_NAME, day))
        
        if res and res[0]['status'] == 'completed':
            # logger.debug(f"日期 {day} 已完成，跳过")
            continue

        # 开始处理
        start_time = time.time()
        biz_date = f"{day[:4]}-{day[4:6]}-{day[6:]}"
        
        try:
            # 抓取数据
            kline_models = await collector.fetch_batch_daily_kline(biz_date)
            
            if kline_models:
                # 批量入库
                affected = await save_batch_fast(kline_models)
                
                # 更新进度 (同步记录)
                upsert_sql = """
                INSERT INTO sync_progress (task_name, current_code, status, last_index, total_count)
                VALUES (%s, %s, 'completed', %s, %s)
                ON DUPLICATE KEY UPDATE status='completed', last_index=%s, updated_at=CURRENT_TIMESTAMP
                """
                await execute_query(upsert_sql, (TASK_NAME, day, idx + 1, total_days, idx + 1))
                
                duration = time.time() - start_time
                logger.info(f"[{idx+1}/{total_days}] {biz_date} 同步成功: {len(kline_models)} 行 (耗时: {duration:.2f}s)")
            else:
                logger.warning(f"[{idx+1}/{total_days}] {biz_date} 无数据返回，可能非交易日或接口异常")
                # 即使无数据也标记为完成，防止死循环
                await execute_query(upsert_sql, (TASK_NAME, day, idx + 1, total_days, idx + 1))

            # [E13-S2-AC1] 强制限流
            await asyncio.sleep(THROTTLE_SLEEP)

        except Exception as e:
            logger.error(f"[{idx+1}/{total_days}] {biz_date} 同步失败: {e}")
            await asyncio.sleep(5) # 发生错误时多等一会儿

    logger.info(">>> 全量回填任务圆满结束 <<<")

if __name__ == "__main__":
    try:
        asyncio.run(run_backfill())
    except KeyboardInterrupt:
        logger.info("任务被手动中断")
    finally:
        # 显式关闭连接池
        loop = asyncio.get_event_loop()
        loop.run_until_complete(DBManager.close_pool())
