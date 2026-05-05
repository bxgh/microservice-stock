import asyncio
import aiomysql
import sys
import os

# 加载配置
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.config import settings

async def check(table_name: str):
    conn = await aiomysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        db=settings.DB_NAME
    )
    async with conn.cursor() as cur:
        try:
            await cur.execute(f"SHOW CREATE TABLE {table_name}")
            res = await cur.fetchone()
            print(res[1])
        except Exception as e:
            print(f"Error: {e}")
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 show_schema.py <table_name>")
        sys.exit(1)
    asyncio.run(check(sys.argv[1]))
