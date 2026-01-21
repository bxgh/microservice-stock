import asyncio
import os
import sys
import httpx

# Ensure app is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.utils.database import db
from app.services.shareholder_service import ShareholderService
from app.utils.logger import get_logger

# Configure logger to output to stdout for script visibility
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("retry_script")

async def get_all_stock_codes():
    """Fetching all stock codes from stock-codes service"""
    url = "http://stock-codes:8000/api/v1/stocks"
    all_codes = set()
    skip = 0
    limit = 1000
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                resp = await client.get(
                    url, 
                    params={"security_type": "stock", "is_listed": "true", "limit": limit, "skip": skip}
                )
                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break
                    
                for item in items:
                    code = item.get("standard_code")
                    # Filter B-shares if necessary (900/200) - Keeping simple for now
                    if code.startswith("900") or code.startswith("200"): 
                        continue
                    all_codes.add(code)
                
                if len(items) < limit:
                    break
                skip += limit
                logger.info(f"Fetched {len(all_codes)} codes...")
            except Exception as e:
                logger.error(f"Error fetching stock codes: {e}")
                return set()
                
    return all_codes

async def get_synced_codes():
    """Get codes already in database"""
    sql = "SELECT DISTINCT ts_code FROM stock_shareholder_count"
    rows = await db.execute(sql)
    return {row[0] for row in rows}

async def main():
    logger.info("Starting retry mechanism...")
    
    # 1. Connect DB
    await db.connect()
    
    try:
        # 2. Get Synced Codes
        synced_codes = await get_synced_codes()
        logger.info(f"Currently synced stocks: {len(synced_codes)}")
        
        # 3. Get All Codes
        all_codes = await get_all_stock_codes()
        logger.info(f"Total target stocks: {len(all_codes)}")
        
        # 4. Calculate Missing
        missing_codes = list(all_codes - synced_codes)
        logger.info(f"Missing stocks: {len(missing_codes)}")
        
        if not missing_codes:
            logger.info("All stocks synced!")
            return
            
        # 5. Batch Sync
        service = ShareholderService()
        batch_size = 20
        total = len(missing_codes)
        
        for i in range(0, total, batch_size):
            batch = missing_codes[i : i + batch_size]
            logger.info(f"Syncing batch {i//batch_size + 1} ({len(batch)} stocks)...")
            
            try:
                result = await service.sync_batch(batch, all_history=True)
                logger.info(f"Batch result: Success={result['success']}, Failed={result['failed']}")
                if result['failed'] > 0:
                     logger.warning(f"Failures: {result['failures']}")
            except Exception as e:
                logger.error(f"Batch failed: {e}")
                
            # Sleep slightly to avoid overwhelming
            await asyncio.sleep(1)
            
    finally:
        await db.disconnect()
        logger.info("Retry process completed.")

if __name__ == "__main__":
    asyncio.run(main())
