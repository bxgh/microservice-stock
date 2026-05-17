import os
import sys
import asyncio
import logging
import time
import datetime
import aiomysql
import pandas as pd
from dotenv import load_dotenv

# 加载项目根目录的 .env (在容器中是 /app/.env)
load_dotenv("/app/.env")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("StandaloneBackfill")

# 环境参数
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "stock")
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")

THROTTLE_SLEEP = 1.2
TASK_NAME = 'full_market_backfill'

async def get_db_conn():
    """获取数据库连接"""
    try:
        return await aiomysql.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            db=DB_NAME, autocommit=True
        )
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return None

async def get_trading_days(conn):
    """获取所有交易日 (兼容 SSE 和 SH 口径)"""
    async with conn.cursor(aiomysql.DictCursor) as cur:
        # 去掉 exchange='SSE' 的限制，使用 DISTINCT 确保唯一性
        await cur.execute("SELECT DISTINCT cal_date FROM trade_cal WHERE is_open=1 ORDER BY cal_date ASC")
        rows = await cur.fetchall()
        return [r['cal_date'].strftime('%Y%m%d') if isinstance(r['cal_date'], datetime.date) else str(r['cal_date']).replace('-', '') for r in rows]

async def run_backfill():
    import tushare as ts
    pro = ts.pro_api(TUSHARE_TOKEN)
    
    conn = await get_db_conn()
    if not conn:
        return

    all_days = await get_trading_days(conn)
    total_days = len(all_days)
    
    # 获取进度
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute("SELECT current_code FROM sync_progress WHERE task_name=%s", (TASK_NAME,))
        prog_res = await cur.fetchone()
        last_sync_day = prog_res['current_code'] if prog_res else "00000000"
    
    logger.info(f">>> 启动独立回填引擎 v1.5 (修复日历口径) | 目标日期: {total_days} | 上次进度: {last_sync_day} <<<")

    for idx, day in enumerate(all_days):
        if day <= last_sync_day:
            continue

        try:
            # 1. 检查连接
            try:
                await conn.ping()
            except:
                logger.warning("数据库连接丢失，正在尝试重连...")
                conn = await get_db_conn()
                if not conn:
                    await asyncio.sleep(10)
                    continue

            biz_date = f"{day[:4]}-{day[4:6]}-{day[6:]}"
            
            # 2. 打印进度条
            progress = (idx + 1) / total_days
            bar = '█' * int(20 * progress) + '-' * (20 - int(20 * progress))
            print(f"\r进度: |{bar}| {progress*100:.1f}% [{idx+1}/{total_days}] 处理 {biz_date}", end="", flush=True)

            # 3. 抓取
            df = pro.daily(trade_date=day)
            
            if not df.empty:
                records = []
                for _, row in df.iterrows():
                    records.append((
                        row['ts_code'], biz_date, float(row['open']), float(row['high']),
                        float(row['low']), float(row['close']), float(row['pre_close']),
                        round(float(row['pct_chg']) / 100.0, 6),
                        float(row['vol']), round(float(row['amount']) * 1000.0, 2)
                    ))
                
                sql_insert = """
                INSERT INTO stock_kline_daily (
                    ts_code, trade_date, open, high, low, close, pre_close, pct_chg, volume, amount
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    open=VALUES(open), high=VALUES(high), low=VALUES(low), close=VALUES(close),
                    pre_close=VALUES(pre_close), pct_chg=VALUES(pct_chg), volume=VALUES(volume), amount=VALUES(amount)
                """
                async with conn.cursor() as cur:
                    await cur.executemany(sql_insert, records)
                
                # 4. 更新进度
                sql_prog = """
                INSERT INTO sync_progress (task_name, current_code, status, last_index, total_count)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    status=VALUES(status), 
                    current_code=VALUES(current_code),
                    last_index=VALUES(last_index), 
                    updated_at=CURRENT_TIMESTAMP
                """
                async with conn.cursor() as cur:
                    await cur.execute(sql_prog, (TASK_NAME, day, 'completed', idx + 1, total_days))
            
            await asyncio.sleep(THROTTLE_SLEEP)
            
        except Exception as e:
            print(f"\n[Error] {day} 发生异常: {e}")
            await asyncio.sleep(10)

    if conn:
        conn.close()
    logger.info("\n>>> 全量回填任务圆满结束 <<<")

if __name__ == "__main__":
    if not TUSHARE_TOKEN:
        print("Error: TUSHARE_TOKEN not found in .env")
        sys.exit(1)
    asyncio.run(run_backfill())
