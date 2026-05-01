import asyncio
import sys
import os

# 将 /app 加入 sys.path 以便导入 app
sys.path.append('/app')

from app.utils.database import db

async def migrate():
    try:
        await db.connect()
        print("Connected to DB")
        
        # 1. stock_analyst_rank
        print("Migrating stock_analyst_rank...")
        await db.execute('ALTER TABLE stock_analyst_rank CHANGE COLUMN stock_code ts_code VARCHAR(20)')
        
        # 2. stock_performance_forecast (Verify it already has ts_code, then rename if needed - but wait, inventory said it has ts_code)
        
        # 3. stock_sentiment_daily
        print("Migrating stock_sentiment_daily...")
        await db.execute('ALTER TABLE stock_sentiment_daily CHANGE COLUMN stock_code ts_code VARCHAR(20)')
        
        # 4. stock_kline_daily (Step 1: ADD COLUMN ts_code)
        # Note: Large table, be careful. For now just add column if not exists.
        print("Adding ts_code to stock_kline_daily...")
        # Check if exists first
        # (Simple approach: try to add, catch error if already exists)
        try:
            await db.execute('ALTER TABLE stock_kline_daily ADD COLUMN ts_code VARCHAR(20) AFTER code')
            print("Added ts_code to stock_kline_daily")
            print("Copying data from code to ts_code in stock_kline_daily...")
            await db.execute('UPDATE stock_kline_daily SET ts_code = code WHERE ts_code IS NULL')
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("Column ts_code already exists in stock_kline_daily")
            else:
                raise e
        
        print("Migration DONE")
    except Exception as e:
        print(f"Migration FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(migrate())
