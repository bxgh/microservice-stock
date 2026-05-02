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
        await cur.execute("SHOW CREATE TABLE stock_kline_daily")
        res = await cur.fetchone()
        print(res[1])
    conn.close()

if __name__ == "__main__":
    asyncio.run(check())
