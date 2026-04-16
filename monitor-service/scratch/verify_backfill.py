import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append("/home/ubuntu/microservice-stock/monitor-service")

from app.utils.database import db

async def check():
    await db.connect()
    try:
        tables = {
            "stock_lhb_daily": "2026-02-01",
            "market_margin_summary": "2026-04-04",
            "stock_block_trade": "2026-01-24"
        }
        
        for table, start_date in tables.items():
            res = await db.execute(f"SELECT COUNT(*), MAX(trade_date) FROM {table} WHERE trade_date >= '{start_date}'")
            print(f"Table {table}: Count={res[0][0]}, Latest={res[0][1]}")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check())
