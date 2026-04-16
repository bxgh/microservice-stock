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
logger = logging.getLogger("backfill_phase1")

AKSHARE_API_URL = settings.AKSHARE_API_URL # This is http://akshare-api:8003/api/v1

async def fetch_data(endpoint):
    url = f"{AKSHARE_API_URL}{endpoint}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in [404, 204]:
                return []
            else:
                logger.error(f"Failed to fetch {url}: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

def format_ts_code(code):
    if not code: return code
    code = str(code)
    if code.startswith('6'): return f"{code}.SH"
    if code.startswith('0') or code.startswith('3'): return f"{code}.SZ"
    if code.startswith('8') or code.startswith('4'): return f"{code}.BJ"
    return code

async def backfill_lhb(start_date, end_date):
    logger.info(f"Starting LHB backfill from {start_date} to {end_date}")
    curr = start_date
    while curr <= end_date:
        ds = curr.strftime("%Y-%m-%d")
        data = await fetch_data(f"/dragon_tiger/daily?date={ds}")
        if data:
            query = """
                INSERT INTO stock_lhb_daily (ts_code, trade_date, close_price, change_pct, turnover_rate, net_buy_amt, reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE close_price=VALUES(close_price), change_pct=VALUES(change_pct), net_buy_amt=VALUES(net_buy_amt)
            """
            args = [(format_ts_code(i.get("code")), i.get("date") or ds, i.get("close"), i.get("change_pct"), i.get("turnover_rate"), i.get("net_buy"), i.get("reason")) for i in data]
            await db.execute_many(query, args)
            logger.info(f"LHB: Saved {len(args)} for {ds}")
        await asyncio.sleep(0.5)
        curr += timedelta(days=1)

async def backfill_margin(start_date, end_date):
    # Note: market_margin_summary requires summary data. Akshare has stock_margin_common_info
    # Since our akshare-api doesn't have a macro margin endpoint yet, we will call akshare directly IF it were installed, 
    # but we should use the API. Let's assume we implement it or skip if not available.
    # Actually, I'll bypass and use a direct SQL aggregation from daily_basic if possible, or skip for now.
    # Wait, daily_basic has PE/PB but not margin.
    logger.info("Margin summary backfill skipped - needs new API endpoint implementation.")

async def backfill_block_trade(start_date, end_date):
    logger.info(f"Starting Block Trade backfill from {start_date} to {end_date}")
    curr = start_date
    while curr <= end_date:
        ds = curr.strftime("%Y-%m-%d")
        data = await fetch_data(f"/block_trade/daily?date={ds}")
        if data:
            query = """
                INSERT INTO stock_block_trade (trade_date, ts_code, price, vol, amt, buyer, seller, type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE price=VALUES(price), amt=VALUES(amt)
            """
            # AkShare block trade keys: code, price, volume, amount, buyer, seller, type, date
            args = []
            for i in data:
                 args.append((
                     i.get("date") or ds,
                     format_ts_code(i.get("code")),
                     i.get("price"),
                     i.get("volume"),
                     i.get("amount"),
                     i.get("buyer"),
                     i.get("seller"),
                     i.get("type")
                 ))
            await db.execute_many(query, args)
            logger.info(f"BlockTrade: Saved {len(args)} for {ds}")
        await asyncio.sleep(0.5)
        curr += timedelta(days=1)

async def main():
    await db.connect()
    try:
        # Phase 1: LHB
        await backfill_lhb(datetime(2026, 2, 1), datetime(2026, 4, 15))
        # Phase 1: Block Trade
        await backfill_block_trade(datetime(2026, 1, 24), datetime(2026, 4, 15))
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
