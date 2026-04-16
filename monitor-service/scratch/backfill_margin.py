import asyncio
import logging
import sys
from datetime import datetime
import httpx

# Add project root to sys.path
sys.path.append("/home/ubuntu/microservice-stock/monitor-service")

from app.utils.database import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("backfill_margin")

AKSHARE_API_URL = "http://localhost:8003/api/v1"

async def main():
    await db.connect()
    try:
        url = f"{AKSHARE_API_URL}/margin/summary"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch margin summary: {resp.status_code}")
                return
            
            data = resp.json()
            if not data:
                logger.info("No margin summary data returned")
                return
            
            query = """
                INSERT INTO market_margin_summary (trade_date, margin_buy, margin_balance)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                margin_buy=VALUES(margin_buy),
                margin_balance=VALUES(margin_balance)
            """
            
            args = []
            for item in data:
                args.append((
                    item.get("date"),
                    item.get("margin_buy"),
                    item.get("margin_balance")
                ))
            
            await db.execute_many(query, args)
            logger.info(f"Successfully saved {len(args)} margin summary records")
            
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
