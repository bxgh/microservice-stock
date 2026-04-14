import asyncio
import os
import time
from dotenv import load_dotenv
import aiomysql

load_dotenv()

async def migrate_table(table_name, id_column="id"):
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
                await cur.execute(f"SELECT MIN({id_column}), MAX({id_column}) FROM {table_name}")
                min_id, max_id = await cur.fetchone()
                
                if min_id is None:
                    print(f"Table {table_name} is empty.")
                    conn.close()
                    return

                print(f"Migrating {table_name} from {min_id} to {max_id}...")
                
                chunk_size = 100000
                current_id = min_id
                
                # Try to find where we left off (heuristic: first non-migrated row)
                # But better to just iterate chunks and only update non-migrated ones.
                
                while current_id <= max_id:
                    end_id = current_id + chunk_size
                    sql = f"""
                        UPDATE {table_name} 
                        SET code = CONCAT(SUBSTRING(code, 4), '.', UPPER(LEFT(code, 2))) 
                        WHERE {id_column} >= %s AND {id_column} < %s 
                        AND (code LIKE 'sh.%%' OR code LIKE 'sz.%%' OR code LIKE 'bj.%%')
                    """
                    res = await cur.execute(sql, (current_id, end_id))
                    if res > 0:
                        print(f"[{table_name}] Range {current_id} - {end_id}: Updated {res} rows")
                    
                    current_id = end_id
                
                print(f"Migration for {table_name} finished.")
                conn.close()
                return # Success

        except Exception as e:
            print(f"Connection lost or error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)
            # Reconnect in next loop

async def main():
    await migrate_table("stock_kline_daily")

if __name__ == "__main__":
    asyncio.run(main())
