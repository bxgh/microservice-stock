import asyncio
import aiomysql
import sys
import time
from datetime import datetime

sys.path.append('/app')
from app.config import settings

async def migrate():
    print(f"[{datetime.now()}] 启动增量影子表同步任务 (V3 - 最后 1% 冲刺版)...")
    
    try:
        conn = await aiomysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            db=settings.DB_NAME,
            autocommit=True
        )
        
        async with conn.cursor() as cur:
            await cur.execute("SELECT MAX(id) FROM stock_kline_daily")
            max_id = (await cur.fetchone())[0]
            
            # 直接从 21100000 开始，这是刚才断开的地方
            start_id = 21100000 
            print(f"当前目标 Max ID: {max_id}, 从 {start_id} 开始最后冲刺")
            
            batch_size = 50000
            current_id = start_id
            
            while current_id <= max_id:
                start_time = time.time()
                
                sql = """
                INSERT IGNORE INTO stock_kline_daily_new 
                (ts_code, trade_date, open, high, low, close, pre_close, volume, amount, turnover, pct_chg, trade_status, created_at)
                SELECT ts_code, trade_date, open, high, low, close, pre_close, volume, amount, turnover, pct_chg, trade_status, created_at
                FROM stock_kline_daily 
                WHERE id BETWEEN %s AND %s
                """
                await cur.execute(sql, (current_id, current_id + batch_size - 1))
                
                rows = cur.rowcount
                elapsed = time.time() - start_time
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 冲刺中... 已处理至 ID: {current_id + batch_size} | 耗时: {elapsed:.2f}s")
                
                current_id += batch_size
                await asyncio.sleep(0.5) # 稍微慢一点，保护数据库
                
        print(f"[{datetime.now()}] 数据迁移【最终完成】！")
        conn.close()
        
    except Exception as e:
        print(f"冲刺异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(migrate())
