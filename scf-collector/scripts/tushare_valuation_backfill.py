import os
import sys
import asyncio
import logging
import time
import datetime
from typing import List, Dict, Any, Optional

# 1. 路径修复：确保能从 scf-collector/shared 加载模块
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(root_dir, ".env"), override=True)

from shared.collectors.tushare_cl import TushareCollector
from shared.db.connection import DBManager, execute_query

# 配置日志
log_dir = os.path.join(root_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(log_dir, 'tushare_valuation_backfill.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger("ValuationBackfill")

# Throttling 策略:
# daily_basic 和 margin_detail 都是 200次/分钟 的流控限制。
# 每次请求后强行休眠 0.35s，以绝对不触发 Tushare 限流，保持单线程极其稳定。
THROTTLE_SLEEP = 0.35
TASK_NAME_DAILY_BASIC = 'tushare_daily_basic_backfill'
TASK_NAME_MARGIN_DETAIL = 'tushare_margin_detail_backfill'

async def get_trading_days(start_date: str) -> List[str]:
    """从数据库获取从起始日期起的所有 A 股交易日"""
    sql = "SELECT cal_date FROM trade_cal WHERE is_open=1 AND exchange='SH' AND cal_date >= %s ORDER BY cal_date ASC"
    rows = await execute_query(sql, (start_date,), is_select=True)
    days = []
    for r in rows:
        d = r['cal_date']
        if isinstance(d, datetime.date):
            days.append(d.strftime('%Y%m%d'))
        else:
            days.append(str(d).replace('-', ''))
    return days

async def save_daily_basic_batch(data: List[Dict[str, Any]]) -> int:
    """批量保存估值指标到 daily_basic"""
    if not data:
        return 0
        
    sql = """
    INSERT INTO daily_basic (
        ts_code, trade_date, close, turnover_rate, turnover_rate_f, volume_ratio,
        pe, pe_ttm, pb, ps, ps_ttm, dv_ratio, dv_ttm,
        total_share, float_share, free_share, total_mv, circ_mv
    ) VALUES (
        %(ts_code)s, %(trade_date)s, %(close)s, %(turnover_rate)s, %(turnover_rate_f)s, %(volume_ratio)s,
        %(pe)s, %(pe_ttm)s, %(pb)s, %(ps)s, %(ps_ttm)s, %(dv_ratio)s, %(dv_ttm)s,
        %(total_share)s, %(float_share)s, %(free_share)s, %(total_mv)s, %(circ_mv)s
    ) ON DUPLICATE KEY UPDATE 
        close = VALUES(close), turnover_rate = VALUES(turnover_rate), turnover_rate_f = VALUES(turnover_rate_f),
        volume_ratio = VALUES(volume_ratio), pe = VALUES(pe), pe_ttm = VALUES(pe_ttm),
        pb = VALUES(pb), ps = VALUES(ps), ps_ttm = VALUES(ps_ttm),
        dv_ratio = VALUES(dv_ratio), dv_ttm = VALUES(dv_ttm), total_share = VALUES(total_share),
        float_share = VALUES(float_share), free_share = VALUES(free_share),
        total_mv = VALUES(total_mv), circ_mv = VALUES(circ_mv)
    """
    
    pool = await DBManager.get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(sql, data)
            return cur.rowcount

async def save_margin_detail_batch(data: List[Dict[str, Any]]) -> int:
    """批量保存融资融券明细到 ods_margin_detail"""
    if not data:
        return 0
        
    sql = """
    INSERT INTO ods_margin_detail (
        ts_code, trade_date, name, rzye, rzmre, rzche, rqye, rqyl, rqchl, rqmcl, rzrqye
    ) VALUES (
        %(ts_code)s, %(trade_date)s, %(name)s, %(rzye)s, %(rzmre)s, %(rzche)s, %(rqye)s, %(rqyl)s, %(rqchl)s, %(rqmcl)s, %(rzrqye)s
    ) ON DUPLICATE KEY UPDATE 
        name = VALUES(name), rzye = VALUES(rzye), rzmre = VALUES(rzmre), rzche = VALUES(rzche),
        rqye = VALUES(rqye), rqyl = VALUES(rqyl), rqchl = VALUES(rqchl), rqmcl = VALUES(rqmcl), rzrqye = VALUES(rzrqye)
    """
    
    pool = await DBManager.get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(sql, data)
            return cur.rowcount

import math

def parse_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f_val = float(val)
        if math.isnan(f_val) or math.isinf(f_val):
            return None
        return f_val
    except (ValueError, TypeError):
        return None

async def run_backfill(start_date: str = "2010-01-01"):
    """主回填逻辑"""
    logger.info(f">>> 启动 Tushare 估值指标与两融明细回填引擎 (E13-S5) <<<")
    logger.info(f"回填起始日期: {start_date}")
    
    try:
        collector = TushareCollector()
        if not collector.pro:
            logger.error("TUSHARE_TOKEN 未配置，任务终止")
            return

        # 1. 获取目标交易日列表
        all_days = await get_trading_days(start_date)
        total_days = len(all_days)
        if total_days == 0:
            logger.error("未找到交易日历数据，请检查 trade_cal 表")
            return
            
        logger.info(f"待处理交易日总数: {total_days}")

        overall_start_time = time.time()

        # 2. 按交易日循环
        for idx, day in enumerate(all_days):
            db_date = f"{day[:4]}-{day[4:6]}-{day[6:]}"
            
            # 检查是否已完成
            check_db_sql = "SELECT status FROM sync_progress WHERE task_name=%s AND current_code=%s"
            db_res = await execute_query(check_db_sql, (TASK_NAME_DAILY_BASIC, day))
            margin_res = await execute_query(check_db_sql, (TASK_NAME_MARGIN_DETAIL, day))
            
            db_done = db_res and db_res[0]['status'] == 'completed'
            margin_done = margin_res and margin_res[0]['status'] == 'completed'
            
            if db_done and margin_done:
                continue

            # 计算进度 and ETA
            progress = (idx + 1) / total_days
            elapsed = time.time() - overall_start_time
            avg_time = elapsed / (idx + 1)
            remaining_days = total_days - (idx + 1)
            eta_sec = avg_time * remaining_days
            eta_str = str(datetime.timedelta(seconds=int(eta_sec)))
            
            bar_length = 15
            filled_length = int(round(bar_length * progress))
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            sys.stdout.write(f"\r进度: |{bar}| {progress*100:.1f}% [{idx+1}/{total_days}] 正在处理 {db_date} | ETA: {eta_str}")
            sys.stdout.flush()

            # (1) 处理 daily_basic 估值指标
            if not db_done:
                retries = 3
                for attempt in range(retries):
                    try:
                        logger.info(f"正在拉取 {db_date} 估值数据...")
                        raw_basic = await collector.fetch_daily_basic(day)
                        
                        cleaned_basic = []
                        for row in raw_basic:
                            # 转换并归一化数据
                            tr = parse_float(row.get('turnover_rate'))
                            tr_f = parse_float(row.get('turnover_rate_f'))
                            dv = parse_float(row.get('dv_ratio'))
                            dv_t = parse_float(row.get('dv_ttm'))
                            cleaned_basic.append({
                                "ts_code": row.get('ts_code'),
                                "trade_date": db_date,
                                "close": parse_float(row.get('close')),
                                # turnover_rate / turnover_rate_f 从百分比转换成小数
                                "turnover_rate": tr / 100.0 if tr is not None else None,
                                "turnover_rate_f": tr_f / 100.0 if tr_f is not None else None,
                                "volume_ratio": parse_float(row.get('volume_ratio')),
                                "pe": parse_float(row.get('pe')),
                                "pe_ttm": parse_float(row.get('pe_ttm')),
                                "pb": parse_float(row.get('pb')),
                                "ps": parse_float(row.get('ps')),
                                "ps_ttm": parse_float(row.get('ps_ttm')),
                                # dv_ratio / dv_ttm 从百分比转换成小数
                                "dv_ratio": dv / 100.0 if dv is not None else None,
                                "dv_ttm": dv_t / 100.0 if dv_t is not None else None,
                                "total_share": parse_float(row.get('total_share')),
                                "float_share": parse_float(row.get('float_share')),
                                "free_share": parse_float(row.get('free_share')),
                                "total_mv": parse_float(row.get('total_mv')),
                                "circ_mv": parse_float(row.get('circ_mv'))
                            })
                        
                        if cleaned_basic:
                            await save_daily_basic_batch(cleaned_basic)
                            
                        # 更新进度
                        upsert_sql = """
                        INSERT INTO sync_progress (task_name, current_code, status, last_index, total_count)
                        VALUES (%s, %s, 'completed', %s, %s)
                        ON DUPLICATE KEY UPDATE status='completed', last_index=%s, updated_at=CURRENT_TIMESTAMP
                        """
                        await execute_query(upsert_sql, (TASK_NAME_DAILY_BASIC, day, idx + 1, total_days, idx + 1))
                        await asyncio.sleep(THROTTLE_SLEEP)
                        break
                    except Exception as e:
                        logger.warning(f"拉取 {db_date} 估值数据失败 (尝试 {attempt+1}/{retries}): {e}")
                        await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"拉取 {db_date} 估值数据彻底失败，跳过该日")

            # (2) 处理 margin_detail 两融明细
            if not margin_done:
                retries = 3
                for attempt in range(retries):
                    try:
                        logger.info(f"正在拉取 {db_date} 两融明细数据...")
                        raw_margin = await collector.fetch_margin_detail(day)
                        
                        cleaned_margin = []
                        for row in raw_margin:
                            cleaned_margin.append({
                                "ts_code": row.get('ts_code'),
                                "trade_date": db_date,
                                "name": row.get('name'),
                                "rzye": parse_float(row.get('rzye')),
                                "rzmre": parse_float(row.get('rzmre')),
                                "rzche": parse_float(row.get('rzche')),
                                "rqye": parse_float(row.get('rqye')),
                                "rqyl": parse_float(row.get('rqyl')),
                                "rqchl": parse_float(row.get('rqchl')),
                                "rqmcl": parse_float(row.get('rqmcl')),
                                "rzrqye": parse_float(row.get('rzrqye'))
                            })
                        
                        if cleaned_margin:
                            await save_margin_detail_batch(cleaned_margin)
                            
                        # 更新进度
                        upsert_sql = """
                        INSERT INTO sync_progress (task_name, current_code, status, last_index, total_count)
                        VALUES (%s, %s, 'completed', %s, %s)
                        ON DUPLICATE KEY UPDATE status='completed', last_index=%s, updated_at=CURRENT_TIMESTAMP
                        """
                        await execute_query(upsert_sql, (TASK_NAME_MARGIN_DETAIL, day, idx + 1, total_days, idx + 1))
                        await asyncio.sleep(THROTTLE_SLEEP)
                        break
                    except Exception as e:
                        logger.warning(f"拉取 {db_date} 两融数据失败 (尝试 {attempt+1}/{retries}): {e}")
                        await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"拉取 {db_date} 两融数据彻底失败，跳过该日")

        sys.stdout.write("\n")
        logger.info(">>> 估值与两融数据历史同步完成！ <<<")
    finally:
        await DBManager.close_pool()

if __name__ == "__main__":
    try:
        start_dt = sys.argv[1] if len(sys.argv) > 1 else "2010-01-01"
        asyncio.run(run_backfill(start_dt))
    except KeyboardInterrupt:
        logger.info("回填任务被手动终止")
