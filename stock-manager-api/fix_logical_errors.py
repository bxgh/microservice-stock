import asyncio
import os
import sys

sys.path.append(os.getcwd())

from app.services.market_data_service import MarketDataService
from app.utils.database import db

async def fix():
    print("正在重新同步异常记录...")
    await db.connect()
    service = MarketDataService()
    
    # 重新同步这两条记录
    res1 = await service.sync_stock_daily(ts_code="002102.SZ", trade_date="2018-06-01")
    res2 = await service.sync_stock_daily(ts_code="600313.SH", trade_date="2010-02-23")
    
    print(f"002102.SZ 同步结果: {res1}")
    print(f"600313.SH 同步结果: {res2}")
    
    await db.disconnect()
    print("修复完成。")

if __name__ == "__main__":
    asyncio.run(fix())
