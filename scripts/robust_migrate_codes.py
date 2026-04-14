
import asyncio
import os
import time
import json
import aiomysql
from dotenv import load_dotenv

load_dotenv()

STATE_FILE = "migration_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"table": "stock_kline_daily", "last_id": 0}

def save_state(table, last_id):
    with open(STATE_FILE, "w") as f:
        json.dump({"table": table, "last_id": last_id}, f)

async def migrate_table(table_name, col_name="code", start_id=0):
    print(f"Starting migration for {table_name} (column: {col_name}) from ID {start_id}...")
    
    conn = await aiomysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        autocommit=True
    )
    
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT MAX(id) FROM {table_name}")
        max_id = (await cur.fetchone())[0] or 0
        print(f"Max ID in {table_name}: {max_id}")
        
        chunk_size = 10000
        current_id = start_id
        
        while current_id <= max_id:
            next_id = current_id + chunk_size
            
            # 1. Update legacy codes to standard format. 
            # Use IGNORE to skip duplicates (where standard already exists).
            sql_upd = f"""
                UPDATE IGNORE {table_name}
                SET {col_name} = CONCAT(SUBSTRING({col_name}, 4), '.', UPPER(LEFT({col_name}, 2)))
                WHERE id >= %s AND id < %s
                AND ({col_name} LIKE 'sh.%%' OR {col_name} LIKE 'sz.%%' OR {col_name} LIKE 'bj.%%')
            """
            
            # 2. Delete remaining legacy codes (those that couldn't be updated due to duplicates).
            sql_del = f"""
                DELETE FROM {table_name}
                WHERE id >= %s AND id < %s
                AND ({col_name} LIKE 'sh.%%' OR {col_name} LIKE 'sz.%%' OR {col_name} LIKE 'bj.%%')
            """
            
            try:
                upd_res = await cur.execute(sql_upd, (current_id, next_id))
                del_res = await cur.execute(sql_del, (current_id, next_id))
                
                if upd_res > 0 or del_res > 0:
                    print(f"[{table_name}] ID {current_id}-{next_id}: Updated {upd_res}, Deleted {del_res}")
                
                current_id = next_id
                save_state(table_name, current_id)
                
                # Small sleep to reduce DB pressure
                await asyncio.sleep(0.05)
                
            except Exception as e:
                print(f"Error at ID {current_id}: {e}. Retrying in 5s...")
                await asyncio.sleep(5)
                # Reconnect if needed
                if "Lost connection" in str(e) or "Can't connect" in str(e):
                    conn = await aiomysql.connect(
                        host=os.getenv("DB_HOST"),
                        port=int(os.getenv("DB_PORT", 3306)),
                        user=os.getenv("DB_USER"),
                        password=os.getenv("DB_PASSWORD"),
                        db=os.getenv("DB_NAME"),
                        autocommit=True
                    )
                    cur = await conn.cursor()

    conn.close()
    print(f"Finished migration for {table_name}.")

async def main():
    state = load_state()
    
    # List of (table_name, column_name)
    tasks = [
        ("stock_kline_daily", "code"),
        ("stock_adjust_factor", "code"),
        ("stock_health_ledger", "stock_code"),
        ("stock_suspensions", "ts_code")
    ]
    
    start_table = state["table"]
    
    # Find start index
    start_index = 0
    for idx, (t, c) in enumerate(tasks):
        if t == start_table:
            start_index = idx
            break
    
    for i in range(start_index, len(tasks)):
        table, col = tasks[i]
        start_id = state["last_id"] if table == start_table else 0
        await migrate_table(table, col, start_id)
        # Reset state for next table
        if i + 1 < len(tasks):
            save_state(tasks[i+1][0], 0)
        else:
            save_state("done", 0)

if __name__ == "__main__":
    asyncio.run(main())
