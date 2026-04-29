
import asyncio
import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

async def list_workflow_ids():
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
            await cur.execute("SELECT id, name FROM workflow_definitions")
            rows = await cur.fetchall()
            for r in rows:
                print(f"{r[0]}: {r[1]}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(list_workflow_ids())
