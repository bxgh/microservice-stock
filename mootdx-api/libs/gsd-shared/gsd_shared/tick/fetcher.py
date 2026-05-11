import asyncio
import logging
import aiohttp
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import pytz

from .constants import MOOTDX_TICK_ENDPOINT
from .utils import clean_stock_code
from .deduplicator import TickDeduplicator

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class TickFetcher:
    """
    Unified Tick Data Fetcher
    
    Supports:
    - Mode.REALTIME: Single fast request (for Intraday Collector)
    - Mode.HISTORICAL: Smart matrix/linear search (for Backfill/History)
    """
    
    class Mode(Enum):
        REALTIME = "realtime"
        HISTORICAL = "historical"
        
    def __init__(self, http_session: aiohttp.ClientSession, api_url: str, mode: Mode = Mode.REALTIME):
        self.http = http_session
        self.api_url = api_url.rstrip('/')
        self.mode = mode
        self.deduplicator = TickDeduplicator()

    TARGET_TIME = "09:25"

    async def fetch(
        self,
        ts_code: str,
        trade_date: Optional[str] = None,
        start: int = 0
    ) -> List[Dict[str, Any]]:
        # Clean code
        clean_code = clean_stock_code(ts_code)
        
        # Reset deduplicator counters for this stock
        self.deduplicator.reset_batch_counters()
        # Also clear cache for this specific code to ensure absolute fresh fetch if needed
        # (Actually, reset_batch_counters is usually enough for occurrence based)
        
        # Determine strategy
        if self.mode == self.Mode.REALTIME:
            return await self._fetch_realtime(clean_code, start)
        else:
            return await self._fetch_linear_scan(clean_code, trade_date)

    async def _fetch_realtime(self, code: str, start: int = 0) -> List[Dict]:
        """Single request for realtime update"""
        url = self.api_url + MOOTDX_TICK_ENDPOINT.format(code=code)
        try:
            params = {"start": start}
            async with self.http.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Apply deduplication
                    return [i for i in data if not self.deduplicator.is_duplicate(code, i)]
        except Exception as e:
            logger.debug(f"Tick fetch failed {code}: {e}")
        return []

    async def _fetch_linear_scan(self, code: str, date: Optional[str]) -> List[Dict]:
        """
        Matrix-Stitching Scan for full day data.
        Uses overlapping slices to ensure no data is missed due to API cursor instability.
        """
        url = self.api_url + MOOTDX_TICK_ENDPOINT.format(code=code)
        all_raw_items = []
        max_depth = 50000
        
        # Stability settings: Overlapping slices (25% overlap)
        chunk_offset = 800 
        chunk_step = 600
        current_start = 0
        
        params_base = {"offset": chunk_offset}
        if date:
            # 兼容 2026-02-03 和 20260203 两种格式
            clean_date = date.replace("-", "")
            params_base["date"] = int(clean_date)

        logger.debug(f"🔍 Starting Matrix-Stitching for {code} (date={date})")

        while current_start < max_depth:
            retries = 3
            success = False
            while retries > 0:
                try:
                    params = params_base.copy()
                    params["start"] = current_start
                    async with self.http.get(url, params=params, timeout=15) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data:
                                # Overlap-aware deduplication: 
                                # Reset slice-local occurrence counters but keep the global fingerprint cache.
                                for item in data:
                                    if not self.deduplicator.is_duplicate(code, item):
                                        all_raw_items.append(item)
                                
                                self.deduplicator.reset_batch_counters()
                                
                                # Termination conditions
                                times = [x.get('time', '') for x in data]
                                earliest = min(times) if times else "23:59"
                                if earliest <= self.TARGET_TIME:
                                    return self._final_sort_and_index(all_raw_items)
                                
                                if len(data) < chunk_offset:
                                    return self._final_sort_and_index(all_raw_items)
                                    
                                current_start += chunk_step
                                success = True
                                break
                            else:
                                retries -= 1
                                if retries > 0: await asyncio.sleep(1)
                        else:
                            retries -= 1
                except Exception as e:
                    logger.warning(f"Slice fetch retry {code} @ {current_start}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    retries -= 1
            
            if not success:
                earliest_known = min([x.get('time','') for x in all_raw_items]) if all_raw_items else "??:??"
                if earliest_known > self.TARGET_TIME:
                    logger.error(f"⚠️ Linear fetch truncated for {code} at start={current_start} (Earliest={earliest_known}). Market start not reached.")
                break
                
        return self._final_sort_and_index(all_raw_items)

    def _final_sort_and_index(self, items: List[Dict]) -> List[Dict]:
        """
        Final stable sorting and re-indexing to ensure ClickHouse data integrity.
        """
        if not items: return []
        
        # Sort keys: Time -> Price -> Volume -> Side (for absolute stability)
        def sort_key(x):
            return (
                x.get('time', '00:00'),
                float(x.get('price', 0)),
                float(x.get('volume', x.get('vol', 0))),
                str(x.get('type', x.get('buyorsell', '')))
            )
            
        items.sort(key=sort_key)
        
        # Sequential num assignment (1..N)
        for i, item in enumerate(items):
            item['num'] = i + 1
            
        return items
