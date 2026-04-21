
import asyncio
import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

async def inspect_db():
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
            # print("--- Current Tables ---")
            # await cur.execute("SHOW TABLES")
            # tables = await cur.fetchall()
            # for (table,) in tables:
            #     print(f"- {table}")
            #     # Get row count for each table
            #     await cur.execute(f"SELECT COUNT(*) FROM {table}")
            #     count = await cur.fetchone()
            #     print(f"  Count: {count[0]}")

            print("\n--- Targeted Table Schemas ---")
            targeted_tables = ["stock_health_ledger", "monitor_indicators_history", "daily_basic", "stock_performance_forecast", "stock_analyst_rank"]
            for table in targeted_tables:
                try:
                    await cur.execute(f"DESCRIBE {table}")
                    print(f"\nSchema of {table}:")
                    rows = await cur.fetchall()
                    for row in rows:
                        print(f"  {row[0]}: {row[1]}")
                    
                    await cur.execute(f"SELECT * FROM {table} LIMIT 1")
                    row = await cur.fetchone()
                    print(f"  Sample data: {row}")
                except Exception as e:
                    print(f"\nError accessing {table}: {e}")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_db())
