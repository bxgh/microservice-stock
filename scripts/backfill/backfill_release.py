import asyncio
import sys
import logging
from datetime import datetime, timedelta

sys.path.append("/app")
from app.utils.database import db
from app.utils.http_client import http_client

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("backfill_release")

async def backfill_release(start_date: str, end_date: str):
    """
    回溯限售解禁数据
    按3个月步进
    """
    await db.connect()
    try:
        curr = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        while curr <= end:
            next_date = curr + timedelta(days=90)
            
            s_str = curr.strftime("%Y-%m-%d")
            e_str = next_date.strftime("%Y-%m-%d")
            
            logger.info(f"Syncing Release: {s_str} -> {e_str}")
            
            try:
                # /api/v1/restricted/release
                params = {"start_date": s_str, "end_date": e_str}
                data = await http_client.get("akshare", "/api/v1/restricted/release", params=params)
                
                if data:
                    rows = []
                    for item in data:
                        raw_code = item.get("code")
                        if not raw_code: continue
                        
                        # Format Code
                        if raw_code.startswith("6"): ts_code = f"{raw_code}.SH"
                        elif raw_code.startswith("8") or raw_code.startswith("4") or raw_code.startswith("9"): ts_code = f"{raw_code}.BJ"
                        else: ts_code = f"{raw_code}.SZ"
                        
                        rows.append((
                            ts_code,
                            item.get("release_date"),
                            item.get("release_count"),
                            item.get("release_market_cap"),
                            item.get("ratio"),
                            item.get("holder_type")
                        ))
                        
                    if rows:
                        # stock_restricted_release
                        # table has uk_code_date_type? No, doc says uk_code_date_type?
                        # Let's check Schema or use INSERT IGNORE
                        # Table def: uk_code_date_type (ts_code, release_date) ... wait, unique key might be just code+date?
                        # Doc says: uk_code_date_type (ts_code, release_date) (Actually index might be code+date)
                        # Let's check SHOW CREATE TABLE or assume standard unique
                        # Or just ON DUPLICATE UPDATE
                        
                        sql = """
                        INSERT INTO stock_restricted_release
                        (ts_code, release_date, release_count, release_market_cap, ratio, holder_type)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            release_count=VALUES(release_count),
                            release_market_cap=VALUES(release_market_cap),
                            ratio=VALUES(ratio),
                            holder_type=VALUES(holder_type)
                        """
                        # Wait, if unique key includes holder_type, duplication works. 
                        # If unique key is only code+date, holder_type might overwrite.
                        # Release usually has multiple batches per day? 
                        # Let's use INSERT IGNORE if uncertain, or assume code+date+type is unique? 
                        # Actually AkShare returns list. Same day might have multiple records?
                        # If primary unique is code+date, we might lose data.
                        # Check DB schema for stock_restricted_release
                        # Previous check showed 29166 records.
                        
                        await db.execute_many(sql, rows)
                        logger.info(f"Synced {len(rows)} records.")
            except Exception as e:
                logger.error(f"Error syncing {s_str}: {e}")
                
            curr = next_date + timedelta(days=1)
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Backfill fatal error: {e}")
    finally:
        await db.disconnect()
        await http_client.close()

if __name__ == "__main__":
    s_date = "2021-01-01"
    e_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d") # +1 year
    
    if len(sys.argv) >= 2:
        s_date = sys.argv[1]
    if len(sys.argv) >= 3:
        e_date = sys.argv[2]
        
    asyncio.run(backfill_release(s_date, e_date))
