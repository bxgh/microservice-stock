
import asyncio
import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

async def inspect_db():
    conn = await aiomysql.connect(
        host=os.getenv("DB_HOST", "124.221.80.250"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        autocommit=True
    )
    
    async with conn.cursor() as cur:
        # 1. Check THS Industries
        await cur.execute("SELECT count(*) FROM stock_industry_ths")
        ths_count = (await cur.fetchone())[0]
        print(f"--- 同花顺行业 (stock_industry_ths) ---")
        print(f"总记录数: {ths_count}")
        await cur.execute("SELECT ts_code, l1_name, l2_name, l3_name FROM stock_industry_ths LIMIT 5")
        rows = await cur.fetchall()
        for r in rows:
            print(f"  {r[0]} | {r[1]} | {r[2]} | {r[3]}")
            
        # 2. Check EM Industries
        await cur.execute("SELECT count(*) FROM stock_industry_em")
        em_count = (await cur.fetchone())[0]
        print(f"\n--- 东方财富行业 (stock_industry_em) ---")
        print(f"总记录数: {em_count}")
        await cur.execute("SELECT ts_code, industry_name FROM stock_industry_em LIMIT 5")
        rows = await cur.fetchall()
        for r in rows:
            print(f"  {r[0]} | {r[1]}")
            
        # 3. Check SW Industries
        await cur.execute("SELECT count(*) FROM stock_industry_sw")
        sw_count = (await cur.fetchone())[0]
        print(f"\n--- 申万行业 (stock_industry_sw) ---")
        print(f"总记录数: {sw_count}")
        await cur.execute("SELECT code, l1_name, l2_name, l3_name FROM stock_industry_sw LIMIT 5")
        rows = await cur.fetchall()
        for r in rows:
            print(f"  {r[0]} | {r[1]} | {r[2]} | {r[3]}")

    conn.close()

if __name__ == "__main__":
    asyncio.run(inspect_db())
