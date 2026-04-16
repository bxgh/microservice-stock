import httpx
import logging
from app.core.config import settings

logger = logging.getLogger("monitor-service.akshare")

class AkShareClient:
    def __init__(self):
        self.base_url = settings.AKSHARE_API_URL

    async def get_market_breadth(self):
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/market/breadth")
            resp.raise_for_status()
            return resp.json()

    async def get_north_flow_summary(self):
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/north/flow_summary")
            resp.raise_for_status()
            return resp.json()

    async def get_index_daily(self, symbol: str, start_date: str = "19700101"):
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"symbol": symbol, "start_date": start_date}
            resp = await client.get(f"{self.base_url}/index/daily", params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_sw_index_daily(self, symbol: str):
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"symbol": symbol}
            resp = await client.get(f"{self.base_url}/index/sw_daily", params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_us_index_daily(self, symbol: str = ".NDX"):
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"symbol": symbol}
            resp = await client.get(f"{self.base_url}/index/us_daily", params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_etf_daily(self, symbol: str, start_date: str = "19700101"):
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"symbol": symbol, "start_date": start_date}
            resp = await client.get(f"{self.base_url}/fund/etf_daily", params=params)
            resp.raise_for_status()
            return resp.json()

ak_client = AkShareClient()
