import asyncio
import sys
import os

sys.path.append('/app')
from app.utils.database import db

async def run_migration():
    try:
        await db.connect()
        print("Connected to DB.")
        
        # 1. Add columns if not exists
        try:
            await db.execute("""
                ALTER TABLE stock_performance_forecast 
                ADD COLUMN growth_min DECIMAL(16,4) DEFAULT NULL AFTER type
            """)
            print("Added growth_min.")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("growth_min already exists.")
            else:
                raise e

        try:
            await db.execute("""
                ALTER TABLE stock_performance_forecast 
                ADD COLUMN growth_max DECIMAL(16,4) DEFAULT NULL AFTER growth_min
            """)
            print("Added growth_max.")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("growth_max already exists.")
            else:
                raise e

        # 2. Ensure migrations_history exists
        await db.execute("""
            CREATE TABLE IF NOT EXISTS migrations_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_migration (migration_name)
            )
        """)
        
        await db.execute("INSERT IGNORE INTO migrations_history (migration_name) VALUES ('001_add_forecast_growth_fields')")
        print("Migration records updated.")
        
    except Exception as e:
        print(f"Migration error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_migration())
