import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append("/home/ubuntu/microservice-stock/monitor-service")

from app.utils.database import db

async def show_tables():
    await db.connect()
    try:
        res = await db.execute("SHOW TABLES")
        for row in res:
             print(row[0])
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(show_tables())
