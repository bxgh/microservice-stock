import asyncio
import httpx
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill")

BASE_URL = "http://127.0.0.1:8003/api/v1"

async def backfill_sw_industries(days=30):
    """回补申万行业历史数据"""
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=days)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    
    logger.info(f"回补申万行业: {start_date} ~ {end_date}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{BASE_URL}/index/sw_sync", params={
            "start_date": start_date,
            "end_date": end_date
        })
        logger.info(f"申万行业回补结果: {r.status_code}, {r.text}")

async def backfill_concepts(days=10):
    """回补同花顺概念板块历史数据"""
    today = datetime.date.today()
    
    # 概念板块回补建议分天进行，或者利用 sync 接口的 start/end
    # 但由于概念同步内部有 375 个循环，建议回补天数不要太多
    start_date = (today - datetime.timedelta(days=days)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    
    logger.info(f"回补概念板块: {start_date} ~ {end_date}")
    async with httpx.AsyncClient(timeout=3600.0) as client:
        r = await client.post(f"{BASE_URL}/index/concept_sync", params={
            "start_date": start_date,
            "end_date": end_date
        })
        logger.info(f"概念板块回补结果: {r.status_code}, {r.text}")

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if mode == "sw":
        asyncio.run(backfill_sw_industries())
    elif mode == "concept":
        asyncio.run(backfill_concepts())
    else:
        asyncio.run(backfill_sw_industries())
        asyncio.run(backfill_concepts())
