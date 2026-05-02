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
        await cur.execute("SHOW TABLES")
        tables = await cur.fetchall()
        for t in tables:
            print(t[0])
    conn.close()

if __name__ == "__main__":
    asyncio.run(check())
