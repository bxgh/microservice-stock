import asyncio
import logging
import sys
from datetime import datetime, timedelta
import httpx

# Add project root to sys.path
sys.path.append("/home/ubuntu/microservice-stock/monitor-service")

from app.utils.database import db
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("backfill_lhb")

AKSHARE_API_URL = settings.AKSHARE_API_URL

async def fetch_lhb_data(date_str):
    url = f"{AKSHARE_API_URL}/api/v1/dragon_tiger/daily?date={date_str}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404 or resp.status_code == 204:
                return []
            else:
                logger.error(f"Failed to fetch LHB for {date_str}: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching LHB for {date_str}: {e}")
            return None

def format_ts_code(code):
    if code.startswith('6'):
        return f"{code}.SH"
    elif code.startswith('0') or code.startswith('3'):
        return f"{code}.SZ"
    elif code.startswith('8') or code.startswith('4'):
        return f"{code}.BJ"
    return code

async def save_lhb_to_db(data, trade_date):
    if not data:
        logger.info(f"No data for {trade_date}")
        return
    
    query = """
        INSERT INTO stock_lhb_daily 
        (ts_code, trade_date, close_price, change_pct, turnover_rate, net_buy_amt, reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        close_price=VALUES(close_price),
        change_pct=VALUES(change_pct),
        turnover_rate=VALUES(turnover_rate),
        net_buy_amt=VALUES(net_buy_amt),
        reason=VALUES(reason)
    """
    
    args = []
    for item in data:
        ts_code = format_ts_code(item.get("code"))
        args.append((
            ts_code,
            item.get("date") or trade_date,
            item.get("close"),
            item.get("change_pct"),
            item.get("turnover_rate"),
            item.get("net_buy"),
            item.get("reason")
        ))
    
    try:
        await db.execute_many(query, args)
        logger.info(f"Successfully saved {len(args)} records for {trade_date}")
    except Exception as e:
        logger.error(f"Failed to save LHB for {trade_date}: {e}")
        # Log one sample for debugging
        if args: logger.error(f"Sample: {args[0]}")

async def main():
    await db.connect()
    try:
        # Test just one day first
        test_date = "2026-02-02"
        data = await fetch_lhb_data(test_date)
        if data:
            await save_lhb_to_db(data, test_date)
            
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
