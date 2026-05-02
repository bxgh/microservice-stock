import asyncio
import aiomysql
from app.config import settings

async def check():
    conn = await aiomysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        db=settings.DB_NAME
    )
    async with conn.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM stock_kline_daily WHERE ts_code IS NULL")
        res = await cur.fetchone()
        print(f"Missing ts_code count: {res[0]}")
    conn.close()

if __name__ == "__main__":
    asyncio.run(check())
