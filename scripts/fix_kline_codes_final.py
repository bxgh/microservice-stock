import asyncio
import os
import time
from dotenv import load_dotenv
import aiomysql

load_dotenv()

async def migrate_and_deduplicate():
    while True:
        try:
            conn = await aiomysql.connect(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", 3306)),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                db=os.getenv("DB_NAME"),
                autocommit=True
            )
            async with conn.cursor() as cur:
                # 1. 针对最近日期的数据进行去重 (2026-01-20 之后)
                print("Checking recent data for duplicates...")
                sql_dedup = """
                DELETE t1 FROM stock_kline_daily t1
                JOIN stock_kline_daily t2 ON t1.trade_date = t2.trade_date
                WHERE t1.trade_date >= '2026-01-20'
                  AND (t1.code LIKE 'sh.%%' OR t1.code LIKE 'sz.%%' OR t1.code LIKE 'bj.%%')
                  AND t2.code = CONCAT(SUBSTRING(t1.code, 4), '.', UPPER(LEFT(t1.code, 2)))
                """
                affected = await cur.execute(sql_dedup)
                print(f"Removed {affected} recent duplicate rows.")

                # 2. 对最近日期的数据进行强制转换
                print("Normalizing recent data...")
                sql_upd = """
                UPDATE stock_kline_daily 
                SET code = CONCAT(SUBSTRING(code, 4), '.', UPPER(LEFT(code, 2))) 
                WHERE trade_date >= '2026-01-20' 
                  AND (code LIKE 'sh.%%' OR code LIKE 'sz.%%' OR code LIKE 'bj.%%')
                """
                affected = await cur.execute(sql_upd)
                print(f"Normalized {affected} recent rows.")

                # 3. 对历史数据进行分块处理 (Deduplicate + Migrate)
                print("Starting full table migration in chunks...")
                chunk_size = 50000
                current_id = 1
                await cur.execute("SELECT MAX(id) FROM stock_kline_daily")
                max_id = (await cur.fetchone())[0] or 0

                while current_id <= max_id:
                    next_id = current_id + chunk_size
                    
                    # 先删除本块中的重复项
                    sql_chunk_dedup = """
                    DELETE t1 FROM stock_kline_daily t1
                    JOIN stock_kline_daily t2 ON t1.trade_date = t2.trade_date
                    WHERE t1.id >= %s AND t1.id < %s
                      AND (t1.code LIKE 'sh.%%' OR t1.code LIKE 'sz.%%' OR t1.code LIKE 'bj.%%')
                      AND t2.code = CONCAT(SUBSTRING(t1.code, 4), '.', UPPER(LEFT(t1.code, 2)))
                    """
                    await cur.execute(sql_chunk_dedup, (current_id, next_id))

                    # 再更新本块中的旧数据
                    sql_chunk_upd = """
                    UPDATE stock_kline_daily 
                    SET code = CONCAT(SUBSTRING(code, 4), '.', UPPER(LEFT(code, 2))) 
                    WHERE id >= %s AND id < %s 
                      AND (code LIKE 'sh.%%' OR code LIKE 'sz.%%' OR code LIKE 'bj.%%')
                    """
                    res = await cur.execute(sql_chunk_upd, (current_id, next_id))
                    if res > 0:
                        print(f"Chunk {current_id}-{next_id}: Migrated {res} rows")
                    
                    current_id = next_id

                print("Full migration complete.")
                conn.close()
                return

        except Exception as e:
            print(f"Error occurred: {e}. Retrying in 10 seconds...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(migrate_and_deduplicate())
