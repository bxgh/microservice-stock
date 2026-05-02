import asyncio
import sys
import time
import os

sys.path.append('/app')
from app.utils.database import db

async def migrate():
    try:
        await db.connect()
        print("Connected to DB. Resuming background loop for stock_kline_daily.ts_code...")
        
        batch_size = 100000
        total_missing_start = 0
        
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT COUNT(*) FROM stock_kline_daily WHERE ts_code IS NULL")
                res = await cur.fetchone()
                total_missing_start = res[0]
                print(f"Total rows to sync: {total_missing_start}")

            count = 0
            while True:
                start_time = time.time()
                async with conn.cursor() as cur:
                    await cur.execute("UPDATE stock_kline_daily SET ts_code = code WHERE ts_code IS NULL LIMIT %s", (batch_size,))
                    updated = cur.rowcount
                    await conn.commit()
                
                count += updated
                elapsed = time.time() - start_time
                
                if updated > 0:
                    print(f"[{time.strftime('%H:%M:%S')}] Updated {updated} rows. Total in this run: {count}. Progress: {count}/{total_missing_start}. Batch took {elapsed:.2f}s")
                
                if updated < batch_size:
                    print("Verifying completion...")
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT 1 FROM stock_kline_daily WHERE ts_code IS NULL LIMIT 1")
                        if not await cur.fetchone():
                            print("Verification successful. All rows updated.")
                            break
                        else:
                            print("Still some rows remain. Continuing...")
                
                await asyncio.sleep(0.3)

        print("Data migration COMPLETED. (Index will NOT be created per user request)")
        
    except Exception as e:
        print(f"Migration FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(migrate())
