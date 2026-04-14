
import asyncio
import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

async def find_legacy_tables():
    conn = await aiomysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        autocommit=True
    )
    async with conn.cursor() as cur:
        await cur.execute("SHOW TABLES")
        tables = [r[0] for r in await cur.fetchall()]
        print(f"Checking {len(tables)} tables...")
        for t in tables:
            try:
                await cur.execute(f"DESC {t}")
                cols_info = await cur.fetchall()
                cols = [c[0] for c in cols_info]
                
                # Check for columns that might contain stock codes
                target_cols = [c for c in cols if c.lower() in ['code', 'ts_code', 'symbol', 'stock_code', 'stk_code']]
                
                for col in target_cols:
                    await cur.execute(f"SELECT COUNT(*) FROM {t} WHERE {col} LIKE 'sh.%%' OR {col} LIKE 'sz.%%' OR {col} LIKE 'bj.%%' LIMIT 1")
                    count = (await cur.fetchone())[0]
                    if count > 0:
                        print(f"Table [{t}] Column [{col}] has legacy codes.")
                        break
            except Exception as e:
                # print(f"Error checking {t}: {e}")
                pass
    conn.close()

if __name__ == "__main__":
    asyncio.run(find_legacy_tables())
