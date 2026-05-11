import logging
from datetime import datetime
import pytz
from typing import Optional, List, Dict, Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class SyncStatusTracker:
    """
    Unified Tick Sync Status & Offset Tracker
    Provides centralized management for both polling offsets (intraday) 
    and task execution status (batch jobs).
    """
    
    REDIS_STATUS_EXPIRE_SECONDS = 86400 * 7  # 7 days
    OFFSET_KEY_PATTERN = "tick:offset:{date}:{code}"
    CHECKPOINT_KEY_PATTERN = "tick:checkpoint:{date}:{code}"
    STATUS_KEY_PATTERN = "tick_sync:status:{date}"

    def __init__(self, redis_client: Optional[redis.Redis]):
        self.redis = redis_client

    async def update_status(
        self, 
        stock_code: str, 
        trade_date: str, 
        status: str, 
        count: int = 0,
        start_t: str = "",
        end_t: str = "",
        error: str = ""
    ) -> None:
        """Update overall collection status in a Redis Hash"""
        if not self.redis: return
        
        key = self.STATUS_KEY_PATTERN.format(date=trade_date)
        sync_time = datetime.now(CST).isoformat()
        # Format: status|count|start|end|sync_time|error
        value = f"{status}|{count}|{start_t}|{end_t}|{sync_time}|{error}"
        
        try:
            await self.redis.hset(key, stock_code, value)
            await self.redis.expire(key, self.REDIS_STATUS_EXPIRE_SECONDS)
        except Exception as e:
            logger.warning(f"Failed to update status in Redis for {stock_code}: {e}")

    async def save_checkpoint(self, stock_code: str, trade_date: str, offset: int, last_fp: str) -> None:
        """[NEW] 同时保存位点和数据指纹，用于断线重连后的精准补盲"""
        if not self.redis: return
        key = self.CHECKPOINT_KEY_PATTERN.format(date=trade_date, code=self._clean_code(stock_code))
        try:
            # 存储格式: offset|last_fingerprint
            value = f"{offset}|{last_fp}"
            await self.redis.set(key, value, ex=86400)
        except Exception as e:
            logger.error(f"Failed to save checkpoint for {stock_code}: {e}")

    async def load_checkpoints(self, stock_codes: List[str], trade_date: str) -> Dict[str, Dict[str, Any]]:
        """[NEW] 批量加载检查点"""
        if not self.redis: 
            return {self._clean_code(c): {"offset": 0, "last_fp": ""} for c in stock_codes}
        
        clean_codes = [self._clean_code(c) for c in stock_codes]
        keys = [self.CHECKPOINT_KEY_PATTERN.format(date=trade_date, code=c) for c in clean_codes]
        
        results = {}
        try:
            values = await self.redis.mget(keys)
            for code, val in zip(clean_codes, values):
                if val:
                    parts = val.decode().split('|') if isinstance(val, bytes) else val.split('|')
                    results[code] = {
                        "offset": int(parts[0]) if len(parts) > 0 else 0,
                        "last_fp": parts[1] if len(parts) > 1 else ""
                    }
                else:
                    results[code] = {"offset": 0, "last_fp": ""}
        except Exception as e:
            logger.error(f"Failed to load checkpoints in bulk: {e}")
            return {self._clean_code(c): {"offset": 0, "last_fp": ""} for c in stock_codes}
        return results

    async def save_offset(self, stock_code: str, trade_date: str, offset: int) -> None:
        """Save iteration offset (legacy support)"""
        if not self.redis: return
        key = self.OFFSET_KEY_PATTERN.format(date=trade_date, code=self._clean_code(stock_code))
        try:
            await self.redis.set(key, offset, ex=86400)
        except Exception as e:
            logger.error(f"Failed to save offset for {stock_code}: {e}")

    async def load_offsets(self, stock_codes: List[str], trade_date: str) -> Dict[str, int]:
        """Bulk load offsets for a list of stocks to minimize Redis RTT"""
        if not self.redis: 
            return {self._clean_code(c): 0 for c in stock_codes}
        
        clean_codes = [self._clean_code(c) for c in stock_codes]
        keys = [self.OFFSET_KEY_PATTERN.format(date=trade_date, code=c) for c in clean_codes]
        
        offsets = {}
        try:
            values = await self.redis.mget(keys)
            for code, val in zip(clean_codes, values):
                offsets[code] = int(val) if val else 0
        except Exception as e:
            logger.error(f"Failed to load offsets in bulk: {e}")
            return {self._clean_code(c): 0 for c in stock_codes}
        return offsets

    def _clean_code(self, code: str) -> str:
        """Internal helper for standardizing codes in Redis keys"""
        return code.replace('sh', '').replace('sz', '').replace('.SH', '').replace('.SZ', '').replace('.sh', '').replace('.sz', '')
