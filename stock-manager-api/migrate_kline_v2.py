import asyncio
import sys
import time
import os

# 将 /app 加入 sys.path 以便导入 app
sys.path.append('/app')

from app.utils.database import db

async def migrate():
    try:
        await db.connect()
        print("Connected to DB. Starting migration of stock_kline_daily.ts_code...")
        
        # 1. 确保列存在 (虽然之前运行过，但可能失败了)
        try:
            await db.execute('ALTER TABLE stock_kline_daily ADD COLUMN ts_code VARCHAR(20) AFTER code')
            print("Column ts_code added.")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("Column ts_code already exists.")
            else:
                raise e

        # 2. 获取总数
        res = await db.execute("SELECT COUNT(*) FROM stock_kline_daily WHERE ts_code IS NULL")
        remaining = res[0][0] if res else 0
        total_to_update = remaining
        print(f"Total rows to update: {total_to_update}")

        if remaining == 0:
            print("No rows need update. Done.")
            return

        batch_size = 50000
        count = 0
        
        # 3. 循环更新
        async with db.pool.acquire() as conn:
            while remaining > 0:
                start_time = time.time()
                async with conn.cursor() as cur:
                    # 使用普通的 cur.execute 这样可以拿到 rowcount
                    await cur.execute("UPDATE stock_kline_daily SET ts_code = code WHERE ts_code IS NULL LIMIT %s", (batch_size,))
                    updated = cur.rowcount
                    await conn.commit() # autocommit=True in pool, but commit for safety
                
                count += updated
                remaining -= updated
                elapsed = time.time() - start_time
                
                # 计算进度
                progress = (count / total_to_update * 100) if total_to_update > 0 else 100
                print(f"[{progress:6.2f}%] Updated {count}/{total_to_update} rows. Last batch took {elapsed:.2f}s")
                
                if updated == 0:
                    # 再次检查是否真的完事了
                    res = await db.execute("SELECT COUNT(*) FROM stock_kline_daily WHERE ts_code IS NULL LIMIT 1")
                    if not res or res[0][0] == 0:
                        break
                    else:
                        print("Update returned 0 but rows still remain? Retrying...")
                
                # 降低压力，每秒跑一次
                await asyncio.sleep(0.2)

        print("Migration COMPLETED.")
        
        # 4. 建立索引
        print("Creating index idx_ts_code (this may take a few minutes)...")
        await db.execute("CREATE INDEX idx_ts_code ON stock_kline_daily(ts_code)")
        print("Index created successfully.")
        
    except Exception as e:
        print(f"Migration FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(migrate())
