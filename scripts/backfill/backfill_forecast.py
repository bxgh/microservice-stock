import asyncio
import sys
import logging
from datetime import datetime, timedelta
sys.path.append("/app")
from app.utils.database import db
from app.utils.http_client import http_client

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("backfill_forecast")

async def backfill_forecast(start_year: int, end_year: int):
    """
    回溯业绩预告数据
    按季度生成报告期 (03-31, 06-30, 09-30, 12-31)
    """
    await db.connect()
    try:
        periods = []
        for year in range(start_year, end_year + 1):
            periods.extend([
                f"{year}-03-31",
                f"{year}-06-30",
                f"{year}-09-30",
                f"{year}-12-31"
            ])
            
        # 还要加上未来一年的预告（比如现在是2026，可能有2026的预告）
        # end_year + 1
        periods.extend([
            f"{end_year+1}-03-31",
            f"{end_year+1}-06-30",
            f"{end_year+1}-09-30",
            f"{end_year+1}-12-31"
        ])
        
        logger.info(f"Target Periods: {periods}")
        
        for period in periods:
            logger.info(f"Syncing Forecast for {period}...")
            # Call API
            try:
                # /api/v1/forecast?period=YYYY-MM-DD
                data = await http_client.get("akshare", "/api/v1/forecast", params={"period": period})
                
                if not data:
                    logger.info(f"{period}: No data.")
                    continue
                    
                rows = []
                for item in data:
                    code = item.get("stock_code") or item.get("code")
                    if not code: continue
                    
                    # Format Code
                    if not code.startswith(("SH", "SZ", "BJ")):
                        if code.startswith("6"): code = f"{code}.SH"
                        elif code.startswith("8") or code.startswith("4") or code.startswith("9"): code = f"{code}.BJ"
                        elif code.startswith("0") or code.startswith("3"): code = f"{code}.SZ"
                        else: code = f"{code}.SZ"
                        
                    rows.append((
                        code,
                        period,
                        item.get("notice_date"),
                        item.get("type"),
                        item.get("growth_range")
                    ))
                    
                if rows:
                    sql = """
                    INSERT INTO stock_performance_forecast
                    (ts_code, report_period, notice_date, type, growth_range)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        notice_date=VALUES(notice_date),
                        type=VALUES(type),
                        growth_range=VALUES(growth_range),
                        updated_at=CURRENT_TIMESTAMP
                    """
                    await db.execute_many(sql, rows)
                    logger.info(f"{period}: Synced {len(rows)} records.")
                else:
                    logger.info(f"{period}: No valid records found.")
                    
            except Exception as e:
                logger.error(f"Error syncing {period}: {e}")
                
            await asyncio.sleep(1) # Gentle
            
    except Exception as e:
        logger.error(f"Backfill fatal error: {e}")
    finally:
        await db.disconnect()
        await http_client.close()

if __name__ == "__main__":
    import sys
    s_year = 2021
    e_year = datetime.now().year
    
    if len(sys.argv) >= 2:
        s_year = int(sys.argv[1])
    if len(sys.argv) >= 3:
        e_year = int(sys.argv[2])
        
    asyncio.run(backfill_forecast(s_year, e_year))
