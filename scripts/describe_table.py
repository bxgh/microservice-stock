
import asyncio
import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

async def describe_table(table_name):
    try:
        conn = await aiomysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            db=os.getenv("DB_NAME"),
            charset='utf8mb4'
        )
        async with conn.cursor() as cur:
            await cur.execute(f"DESCRIBE {table_name}")
            rows = await cur.fetchall()
            for r in rows:
                print(r)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    table = sys.argv[1] if len(sys.argv) > 1 else "workflow_runs"
    asyncio.run(describe_table(table))
