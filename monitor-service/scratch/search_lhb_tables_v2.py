import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append("/home/ubuntu/microservice-stock/monitor-service")

from app.utils.database import db

async def search():
    await db.connect()
    try:
        print("Searching for LHB seat/trader related tables:")
        res = await db.execute("SHOW TABLES")
        for r in res:
             tbl = r[0]
             if any(keyword in tbl.lower() for keyword in ['lhb', 'seat', 'trader', 'yyb']):
                 print(f"Table Found: {tbl}")
                 cols = await db.execute(f"DESCRIBE {tbl}")
                 print(f"  Columns: {[c[0] for c in cols]}")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(search())
