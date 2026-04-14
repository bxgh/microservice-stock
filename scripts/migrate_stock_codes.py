import asyncio
import os
import time
from dotenv import load_dotenv
import aiomysql

load_dotenv()

async def migrate_table(table_name, id_column="id"):
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
            return

        print(f"Migrating {table_name} from {min_id} to {max_id}...")
        
        chunk_size = 50000
        current_id = min_id
        
        while current_id <= max_id:
            end_id = current_id + chunk_size
            sql = f"""
                UPDATE {table_name} 
                SET code = CONCAT(SUBSTRING(code, 4), '.', UPPER(LEFT(code, 2))) 
                WHERE {id_column} >= %s AND {id_column} < %s 
                AND (code LIKE 'sh.%%' OR code LIKE 'sz.%%' OR code LIKE 'bj.%%')
            """
            try:
                res = await cur.execute(sql, (current_id, end_id))
                if res > 0:
                    print(f"[{table_name}] Filter {current_id} - {end_id}: Updated {res} rows")
            except Exception as e:
                print(f"Error at {current_id}: {e}")
                
            current_id = end_id
            
    conn.close()

async def main():
    await migrate_table("stock_kline_daily")
    await migrate_table("stock_adjust_factor")

if __name__ == "__main__":
    asyncio.run(main())
