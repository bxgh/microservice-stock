import logging
import os
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
import pytz

from .constants import TABLE_INTRADAY_LOCAL, TABLE_HISTORY_LOCAL, TABLE_INTRADAY_DIST, TABLE_HISTORY_DIST
from .utils import clean_stock_code

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class TickWriter:
    """
    Unified Tick Writer
    
    Responsibilities:
    1. Route data to correct LOCAL tables based on date
       - Today -> tick_data_intraday_local (high frequency)
       - History -> tick_data_local (archive)
    2. Normalize fields (Direction, Volume) using standard mapping
    """
    
    class Target(Enum):
        INTRADAY = "intraday"
        HISTORY = "history"
        
    def __init__(self, clickhouse_pool, use_distributed: bool = False):
        """
        Args:
            clickhouse_pool: asynch pool instance
            use_distributed: If True, write to Distributed tables (auto-sharded)
        """
        self.ch_pool = clickhouse_pool
        self.use_distributed = use_distributed or os.getenv("CLICKHOUSE_USE_DISTRIBUTED", "false").lower() == "true"

    async def write(
        self, 
        ts_code: str, 
        trade_date: str, 
        data: List[Dict[str, Any]],
        idempotent: bool = True
    ) -> int:
        """
        Write tick data to ClickHouse.
        Auto-determines target table based on date.
        
        Args:
            ts_code: Stock code
            trade_date: YYYYMMDD
            data: List of tick records
            idempotent: If True, clear existing data for this stock/date before inserting.
                        Recommended for historical backfills.
        
        Returns:
            Number of rows written
        """
        if not self.ch_pool or not data:
            return 0
            
        # 0. Normalize date
        clean_date_str = trade_date.replace("-", "")

        # 1. Determine Target Table
        # POLICY: Forced to history for now as intraday pipeline is paused.
        target_table = TABLE_HISTORY_DIST if self.use_distributed else TABLE_HISTORY_LOCAL
            
        try:
            trade_date_obj = datetime.strptime(clean_date_str, "%Y%m%d").date()
            clean_code = self._clean_code(ts_code)

            # 2. Strong Idempotency: Clear existing data
            if idempotent:
                await self._clear_existing_data(target_table, clean_code, trade_date_obj)

            # 3. Transform Data
            rows = []
            for item in data:
                # Time normalize (HH:MM -> HH:MM:00)
                time_str = str(item.get('time', '09:30'))
                if len(time_str) == 5: time_str += ":00"
                
                # Field Mapping
                price = float(item.get('price', 0))
                # Handle vol vs volume alias
                vol = int(item.get('volume', item.get('vol', 0)))
                # Handle direction string/int mapping
                direction = self._map_direction(item.get('type', item.get('buyorsell', 2)))
                # [FIXED] Extract 'num' (trade index) to prevent deduplication
                # Co-aligned with intraday_tick_collector and fetcher aliases
                num = int(item.get('num', item.get('no', item.get('index', 0))))
                
                rows.append((
                    clean_code,
                    trade_date_obj,
                    time_str,
                    price,
                    vol,
                    price * vol,  # amount approx
                    direction,
                    num
                ))

            if not rows:
                return 0
                
            # 4. Insert into ClickHouse
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        f"INSERT INTO stock_data.{target_table} (ts_code, trade_date, tick_time, price, volume, amount, direction, num) VALUES",
                        rows
                    )
            
            return len(rows)
            
        except Exception as e:
            logger.error(f"Tick write failed for {ts_code} to {target_table}: {e}")
            raise

    async def _clear_existing_data(self, table: str, code: str, date_obj: Any):
        """Execute DELETE mutation for strong idempotency"""
        try:
            # Note: ClickHouse Mutations are asynchronous, but for backfills this is 
            # the standard way to ensure no duplicates without relying on 'FINAL' keyword.
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        f"ALTER TABLE stock_data.{table} DELETE WHERE ts_code = %(code)s AND trade_date = %(date)s",
                        {"code": code, "date": date_obj}
                    )
            logger.debug(f"🗑️ Cleared existing data for {code} on {date_obj} in {table}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to clear existing data for {code}: {e}")

    def _map_direction(self, value: Any) -> int:
        """
        Map direction to UInt8 (0=Buy, 1=Sell, 2=Neutral)
        """
        # String case (from get-stockdata API parsing)
        if isinstance(value, str):
            mapping = {"BUY": 0, "SELL": 1, "NEUTRAL": 2}
            return mapping.get(value.upper(), 2)
            
        # Integer case (from mootdx direct or gsd-worker legacy)
        if isinstance(value, int):
            return value if value in [0, 1, 2] else 2
            
        return 2

    def _clean_code(self, code: str) -> str:
        """Sanitize stock code: remove sh/sz prefixes and dots"""
        return clean_stock_code(code)
