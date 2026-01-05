
import asyncio
import os
import aiomysql
import datetime

async def check_count():
    try:
        conn = await aiomysql.connect(
            host=os.getenv("DB_HOST", "sh-cdb-h7flpxu4.sql.tencentcdb.com"),
            port=int(os.getenv("DB_PORT", 26300)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "alwaysup@888"),
            db=os.getenv("DB_NAME", "alwaysup"),
            charset='utf8mb4'
        )
        async with conn.cursor() as cur:
            target_date = "2025-12-30"
            print(f"Checking count for {target_date}...")
            start = datetime.datetime.now()
            await cur.execute("SELECT COUNT(*) FROM stock_kline_daily WHERE trade_date = %s", (target_date,))
            res = await cur.fetchone()
            end = datetime.datetime.now()
            print(f"Count: {res[0]}, Time: {end - start}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_count())
