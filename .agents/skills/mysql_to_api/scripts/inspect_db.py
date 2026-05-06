import asyncio
import aiomysql
import os
import json
import argparse
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv(os.path.join(os.getcwd(), '.env'))

async def get_db_connection():
    try:
        pool = await aiomysql.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            db=os.getenv("DB_NAME", "stock_data"),
            autocommit=True,
            charset='utf8mb4'
        )
        return pool
    except Exception as e:
        print(json.dumps({"error": f"Failed to connect to database: {str(e)}"}))
        sys.exit(1)

def map_mysql_type_to_python(mysql_type):
    mysql_type = mysql_type.lower()
    if 'int' in mysql_type:
        return 'int'
    elif 'float' in mysql_type or 'double' in mysql_type or 'decimal' in mysql_type:
        return 'float'
    elif 'datetime' in mysql_type or 'timestamp' in mysql_type or 'date' in mysql_type:
        return 'datetime'
    elif 'json' in mysql_type:
        return 'dict'
    else:
        return 'str'

async def inspect_table(pool, table_name):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute(f"DESCRIBE {table_name}")
                rows = await cur.fetchall()
                # Field, Type, Null, Key, Default, Extra
                columns = []
                for row in rows:
                    columns.append({
                        "name": row[0],
                        "type": row[1],
                        "nullable": row[2] == "YES",
                        "key": row[3],
                        "default": row[4],
                        "python_type": map_mysql_type_to_python(row[1])
                    })
                return {"type": "table", "name": table_name, "columns": columns}
            except Exception as e:
                return {"error": str(e)}

async def inspect_sql(pool, sql_query):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                # Limit 1 to get schema
                if "limit" not in sql_query.lower():
                    sql_query += " LIMIT 1"
                
                await cur.execute(sql_query)
                description = cur.description
                columns = []
                for col in description:
                    # description item: (name, type_code, display_size, internal_size, precision, scale, null_ok)
                    # Mapping type_code to string is hard without looking up pymysql constants, 
                    # but we can infer from a returned row if available, or generic 'str'
                    # Actually we can invoke a row fetch
                    pass
                
                # Fetch one row to help with type inference if needed, but primarily rely on description
                # However, description type_code is an integer. 
                # Let's try to get Types from aiomysql/pymysql constants if possible?
                # Simpler approach: Just return names and generic types, or ask LLM to infer.
                # Or, we can do a trick: create a temporary view? No, read only.
                
                # Alternative: Just return the column names. The LLM can handle "Any" or "str" initially.
                # Or improved: execute "SHOW COLUMNS" doesn't work on arbitrary SQL.
                
                # Let's just return column names and sample data type wrapper
                row = await cur.fetchone()
                
                cols = []
                for i, desc in enumerate(description):
                    col_name = desc[0]
                    # Simple inference from python type of the value if row exists
                    py_type = 'str'
                    if row:
                        val = row[i]
                        if isinstance(val, int): py_type = 'int'
                        elif isinstance(val, float): py_type = 'float'
                        elif isinstance(val, dict): py_type = 'dict'
                    
                    cols.append({
                        "name": col_name,
                        "python_type": py_type
                    })
                    
                return {"type": "sql", "sql": sql_query, "columns": cols}

            except Exception as e:
                return {"error": str(e)}

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", help="Table name to inspect")
    parser.add_argument("--sql", help="SQL query to inspect")
    args = parser.parse_args()

    pool = await get_db_connection()

    try:
        if args.table:
            result = await inspect_table(pool, args.table)
        elif args.sql:
            result = await inspect_sql(pool, args.sql)
        else:
            result = {"error": "No table or SQL provided"}
        
        print(json.dumps(result, indent=2))
    finally:
        pool.close()
        await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
