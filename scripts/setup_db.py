import asyncio
import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

async def run():
    print(f"Connecting to {os.getenv('DB_HOST')}...")
    conn = await aiomysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        db=os.getenv('DB_NAME')
    )
    async with conn.cursor() as cur:
        print("Dropping old tables...")
        await cur.execute('DROP TABLE IF EXISTS monitor_indicators_history')
        await cur.execute('DROP TABLE IF EXISTS monitor_health_scores')
        
        print("Creating new monitor_indicators_history...")
        await cur.execute('''
            CREATE TABLE monitor_indicators_history (
                trade_date DATE NOT NULL,
                indicator_name VARCHAR(50) NOT NULL,
                indicator_value DOUBLE,
                score DOUBLE,
                PRIMARY KEY (trade_date, indicator_name),
                KEY idx_date (trade_date),
                KEY idx_name (indicator_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        print("Creating new monitor_health_scores...")
        await cur.execute('''
            CREATE TABLE monitor_health_scores (
                trade_date DATE PRIMARY KEY,
                total_score DOUBLE,
                status VARCHAR(20)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        await conn.commit()
        
        print("Verifying schema...")
        await cur.execute('DESC monitor_indicators_history')
        cols = await cur.fetchall()
        for c in cols:
            print(f"  {c}")
            
    conn.close()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(run())
