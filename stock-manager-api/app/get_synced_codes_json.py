import json
from app.utils.database import db
import asyncio
import os
import sys
sys.path.append('.')


async def main():
    try:
        await db.connect()
        rows = await db.execute('SELECT DISTINCT ts_code FROM stock_shareholder_count')
        codes = [row[0] for row in rows]
        print(json.dumps(codes))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
    finally:
        await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
