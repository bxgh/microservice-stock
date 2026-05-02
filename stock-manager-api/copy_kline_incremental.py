import asyncio
import aiomysql
import sys
import time
from datetime import datetime

sys.path.append('/app')
from app.config import settings

async def migrate():
    print(f"[{datetime.now()}] 启动增量影子表同步任务...")
    
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
            # 1. 获取最大 ID 以确定范围
            await cur.execute("SELECT MIN(id), MAX(id) FROM stock_kline_daily")
            min_id, max_id = await cur.fetchone()
            print(f"ID 范围: {min_id} 到 {max_id}")
            
            # 2. 分批拷贝
            batch_size = 50000
            current_id = min_id
            
            while current_id <= max_id:
                start_time = time.time()
                
                # 执行分批插入
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
                progress = ((current_id - min_id) / (max_id - min_id)) * 100
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 进度: {progress:.2f}% | 已迁移至 ID: {current_id + rows} | 耗时: {elapsed:.2f}s")
                
                current_id += batch_size
                # 稍微停顿一下，降低对线上数据库的压力
                await asyncio.sleep(0.1)
                
        print(f"[{datetime.now()}] 数据迁移完成！请检查新表数据量后执行 RENAME TABLE。")
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(migrate())
