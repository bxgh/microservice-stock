import asyncio
import os
from dotenv import load_dotenv
import aiomysql

load_dotenv()

async def migrate():
    print("Connecting to database...")
    conn = await aiomysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        charset='utf8mb4',
        autocommit=True
    )
    
    async with conn.cursor() as cur:
        # Check existing tables
        await cur.execute("SHOW TABLES")
        tables = await cur.fetchall()
        print(f"Existing tables: {[t[0] for t in tables]}")
        
        # Create commands table
        print("Creating 'commands' table...")
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS commands (
            id INT AUTO_INCREMENT PRIMARY KEY,
            task_id VARCHAR(50) NOT NULL,
            params JSON,
            status VARCHAR(20) DEFAULT 'PENDING',
            result TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            executed_at DATETIME,
            finished_at DATETIME,
            request_id VARCHAR(50)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        await cur.execute(create_table_sql)
        print("Table 'commands' created or already exists.")
        
    conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
