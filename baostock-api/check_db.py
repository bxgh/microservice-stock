import asyncio
from app.utils.database import db

async def check():
    await db.connect()
    try:
        tables = await db.execute("SHOW TABLES")
        print("Tables in Database:")
        for t in tables:
            print(t)
            
        latest = await db.execute("SELECT code, MAX(trade_date) FROM stock_kline_daily GROUP BY code LIMIT 20")
        print("Latest Trade Dates (sample):")
        for row in latest:
            print(row)
            
        progress = await db.execute("SELECT * FROM sync_progress")
        print("Progress Table:")
        for row in progress:
            print(row)
            
        count = await db.execute("SELECT COUNT(*) FROM stock_kline_daily")
        print(f"Total K-lines: {count[0][0]}")
        
        adjust_count = await db.execute("SELECT COUNT(*) FROM stock_adjust_factor")
        print(f"Total Adjust Factors: {adjust_count[0][0]}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check())
