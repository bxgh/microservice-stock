
import asyncio
import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

async def sample_legacy():
    conn = await aiomysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        autocommit=True
    )
    async with conn.cursor() as cur:
        await cur.execute("SELECT id, code FROM stock_kline_daily WHERE code LIKE 'sh.%' LIMIT 10")
        rows = await cur.fetchall()
        print("Legacy rows sample (sh.%):", rows)
        
        await cur.execute("SELECT id, code FROM stock_kline_daily WHERE code LIKE 'sz.%' LIMIT 10")
        rows = await cur.fetchall()
        print("Legacy rows sample (sz.%):", rows)
        
        await cur.execute("SELECT MIN(id), MAX(id) FROM stock_kline_daily WHERE code LIKE 'sh.%'")
        rows = await cur.fetchall()
        print("ID range for sh.%:", rows)

    conn.close()

if __name__ == "__main__":
    asyncio.run(sample_legacy())
