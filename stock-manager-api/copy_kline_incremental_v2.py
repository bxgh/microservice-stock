import asyncio
import aiomysql
import sys
import time
from datetime import datetime

sys.path.append('/app')
from app.config import settings

async def migrate():
    print(f"[{datetime.now()}] 启动增量影子表同步任务 (V2 - 自动断点续传版)...")
    
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
            # 1. 获取最大 ID 确定总范围
            await cur.execute("SELECT MIN(id), MAX(id) FROM stock_kline_daily")
            min_id, max_id = await cur.fetchone()
            
            # 2. 从日志或 ID 范围估算一个安全的起点
            # 由于新表没有自增 ID，我们直接从上次报错的 ID 附近开始（略微重叠以保安全）
            start_id = 19410000 
            print(f"ID 总范围: {min_id} 到 {max_id}, 本次从 {start_id} 断点续传")
            
            # 3. 分批拷贝
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
                progress = ((current_id - min_id) / (max_id - min_id)) * 100
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 进度: {progress:.2f}% | 已迁移至 ID: {current_id + batch_size} | 耗时: {elapsed:.2f}s")
                
                current_id += batch_size
                await asyncio.sleep(0.1)
                
        print(f"[{datetime.now()}] 数据迁移最终完成！")
        conn.close()
        
    except Exception as e:
        print(f"恢复过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(migrate())
