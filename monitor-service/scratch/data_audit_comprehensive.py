import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append("/home/ubuntu/microservice-stock/monitor-service")

from app.utils.database import db

async def audit():
    await db.connect()
    try:
        tables_to_check = [
            "raw_capital_flow_summary",
            "stock_north_funds_daily",
            "stock_lhb_daily",
            "raw_sector_daily",
            "raw_market_stats",
            "stock_sentiment_daily",
            "market_margin_summary",
            "stock_top10_shareholders",
            "stock_restricted_release",
            "trade_cal",
            "daily_basic"
        ]
        
        print(f"{'Table Name':<30} | {'Record Count':<12} | {'Latest Date':<12}")
        print("-" * 60)
        
        for table in tables_to_check:
            try:
                # Get count
                count_res = await db.execute(f"SELECT COUNT(*) FROM {table}")
                count = count_res[0][0] if count_res else 0
                
                # Get latest date (assume trade_date or date)
                date_col = "trade_date"
                # Check column name first
                cols = await db.execute(f"DESCRIBE {table}")
                col_names = [c[0] for c in cols]
                if "trade_date" not in col_names:
                    if "date" in col_names:
                        date_col = "date"
                    else:
                        date_col = None
                
                latest_date = "N/A"
                if date_col and count > 0:
                    latest_res = await db.execute(f"SELECT MAX({date_col}) FROM {table}")
                    latest_date = str(latest_res[0][0]) if latest_res else "N/A"
                
                print(f"{table:<30} | {count:<12} | {latest_date:<12}")
            except Exception as e:
                print(f"{table:<30} | ERROR: {str(e)[:20]}...")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(audit())
