import asyncio
import os
import sys

# Ensure config import
sys.path.append('/app')
from app.utils.database import db

async def fix_schema():
    print("Connecting to database...")
    await db.connect()
    
    try:
        sql = "ALTER TABLE stock_shareholder_count MODIFY COLUMN holder_change_pct DECIMAL(24,6) DEFAULT NULL COMMENT '户数变动比例'"
        print(f"Executing: {sql}")
        await db.execute(sql)
        print("Schema altered successfully.")
    except Exception as e:
        print(f"Error altering schema: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(fix_schema())
