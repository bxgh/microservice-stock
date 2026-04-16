import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), "monitor-service"))
from app.utils.database import db

async def get_schemas():
    await db.connect()
    tables = ['monitor_indicators_history', 'monitor_health_scores']
    for table in tables:
        print(f"\n--- {table} ---")
        try:
            rows = await db.execute(f"DESC {table}")
            for r in rows:
                print(r)
        except Exception as e:
            print(f"Error describing {table}: {e}")
    await db.disconnect()

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(get_schemas())
