import asyncio
import sys
import time
import os

sys.path.append('/app')
from app.utils.database import db

async def migrate():
    try:
        await db.connect()
        print("Connected to DB. Starting background loop for stock_kline_daily.ts_code...")
        
        batch_size = 100000
        count = 0
        
        async with db.pool.acquire() as conn:
            while True:
                start_time = time.time()
                async with conn.cursor() as cur:
                    # 直接更新，不先计算总数
                    await cur.execute("UPDATE stock_kline_daily SET ts_code = code WHERE ts_code IS NULL LIMIT %s", (batch_size,))
                    updated = cur.rowcount
                    await conn.commit()
                
                count += updated
                elapsed = time.time() - start_time
                
                if updated > 0:
                    print(f"[{time.strftime('%H:%M:%S')}] Updated {updated} rows. Total so far: {count}. Batch took {elapsed:.2f}s")
                
                if updated < batch_size:
                    # 再次确认是否真的完事了
                    print("Last batch was smaller than batch_size. Verifying completion...")
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT 1 FROM stock_kline_daily WHERE ts_code IS NULL LIMIT 1")
                        if not await cur.fetchone():
                            print("Verification successful. All rows updated.")
                            break
                        else:
                            print("Still some rows remain. Continuing...")
                
                # 稍微歇一下
                await asyncio.sleep(0.3)

        print("Data migration COMPLETED.")
        
        # 索引创建放在最后
        print("Creating index idx_ts_code...")
        await db.execute("CREATE INDEX idx_ts_code ON stock_kline_daily(ts_code)")
        print("Index created successfully.")
        
    except Exception as e:
        print(f"Migration FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(migrate())
