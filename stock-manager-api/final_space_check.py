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
        await cur.execute(f"SELECT table_name, (data_length + index_length) / 1024 / 1024 AS total_mb FROM information_schema.tables WHERE table_schema = '{settings.DB_NAME}' ORDER BY total_mb DESC LIMIT 10")
        res = await cur.fetchall()
        print("--- Largest Tables ---")
        for r in res:
            print(f"{r[0]}: {r[1]:.2f} MB")
            
        print("\n--- Binlog Status ---")
        await cur.execute("SHOW BINARY LOGS")
        logs = await cur.fetchall()
        total_binlog = sum(log[1] for log in logs)
        print(f"Total Binlog size: {total_binlog / 1024 / 1024:.2f} MB")
        
    conn.close()

if __name__ == "__main__":
    asyncio.run(check())
