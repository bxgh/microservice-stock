"""
Redis Stream Protocol for Tick Data Acquisition
"""
import enum
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field

import redis.asyncio as redis

logger = logging.getLogger("redis_protocol")

# --- Constants ---
STREAM_KEY_JOBS = "stream:tick:jobs"
STREAM_KEY_DATA = "stream:tick:data"
GROUP_MOOTDX_WORKERS = "group:mootdx:workers"
CONSUMER_PREFIX = "worker"

class JobType(str, enum.Enum):
    INTRADAY = "intraday"
    POST_MARKET = "post_market"

class JobStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"

# --- Protocol Models ---

class TickJob(BaseModel):
    """
    采集任务消息协议
    """
    job_id: str = Field(..., description="UUID v4")
    stock_code: str = Field(..., description="股票代码, e.g. 000001")
    type: JobType = Field(default=JobType.POST_MARKET, description="采集类型")
    date: str = Field(..., description="日期 YYYYMMDD")
    market: Optional[str] = Field(None, description="市场 sz/sh, 可选")
    last_vol: int = Field(0, description="[盘中] 上次成交量，用于增量判定")
    retry_count: int = Field(0, description="重试次数")

    def to_redis_dict(self) -> Dict[str, Any]:
        """Convert to flat dict for Redis (filter None and bool)"""
        d = self.model_dump(mode='json')
        return {k: (str(v) if isinstance(v, bool) else v) for k, v in d.items() if v is not None}

class TickResult(BaseModel):
    """
    采集结果消息协议
    """
    job_id: str
    stock_code: str
    date: str = Field(..., description="日期 YYYYMMDD")
    status: JobStatus
    row_count: int = 0
    data_blob: str = Field("", description="JSON serialized list of dicts")
    check_0925: bool = Field(False, description="是否包含09:25数据")
    error_msg: Optional[str] = None

    def to_redis_dict(self) -> Dict[str, Any]:
        """Convert to flat dict for Redis (filter None and bool)"""
        d = self.model_dump(mode='json')
        return {k: (str(v) if isinstance(v, bool) else v) for k, v in d.items() if v is not None}

# --- SDK Client ---

from redis.asyncio.cluster import RedisCluster

class RedisStreamClient:
    """
    封装 Redis Stream 通用操作，支持单机和集群模式
    """
    def __init__(self, redis_url: str, is_cluster: bool = False):
        if is_cluster:
            # Cluster mode uses the url to find nodes
            self.redis = RedisCluster.from_url(redis_url, encoding="utf-8", decode_responses=True)
        else:
            self.redis = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def init_consumer_group(self, stream_key: str, group_name: str):
        """Idempotently create consumer group"""
        try:
            await self.redis.xgroup_create(stream_key, group_name, id="0", mkstream=True)
            logger.info(f"Consumer group {group_name} created on {stream_key}")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group {group_name} already exists")
            else:
                raise e

    async def publish_job(self, job: TickJob) -> str:
        """Push job to stream"""
        return await self.redis.xadd(STREAM_KEY_JOBS, job.to_redis_dict())

    async def publish_result(self, result: TickResult) -> str:
        """Push result to stream"""
        return await self.redis.xadd(STREAM_KEY_DATA, result.to_redis_dict())

    async def consume_jobs(self, stream_key: str, group_name: str, consumer_name: str, count: int = 1, block_ms: int = 5000) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Consume jobs from a stream using a consumer group.
        Returns a list of (msg_id, data_dict).
        """
        try:
            # > implies "new messages" for this consumer in the group
            streams = {stream_key: ">"}
            response = await self.redis.xreadgroup(group_name, consumer_name, streams, count=count, block=block_ms)
            
            # Response format: [[stream_name, [[msg_id, {data}], ...]]]
            parsed_messages = []
            if response:
                for stream_name, messages in response:
                    for msg_id, data in messages:
                        parsed_messages.append((msg_id, data))
            return parsed_messages
        except Exception as e:
            logger.error(f"Error consuming stream {stream_key}: {e}")
            return []

    async def claim_pending_jobs(self, stream_key: str, group_name: str, consumer_name: str, min_idle_time_ms: int = 60000, count: int = 10) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Claim pending jobs from other consumers that have been idle for too long.
        """
        try:
            # XAUTOCLAIM key group consumer min-idle-time start [COUNT count] [JUSTID]
            # Returns: [start_id, [[msg_id, {data}], ...]]
            # We use '0-0' as start_id to scan from beginning of PEL
            start_id = "0-0"
            result = await self.redis.xautoclaim(stream_key, group_name, consumer_name, min_idle_time_ms, start_id, count=count)
            
            messages = result[1] # The list of messages
            parsed_messages = []
            if messages:
                 for msg_id, data in messages:
                    parsed_messages.append((msg_id, data))
            return parsed_messages
        except Exception as e:
            logger.error(f"Error claiming pending jobs {stream_key}: {e}")
            return []

    async def ack_job(self, stream_key: str, group_name: str, *msg_ids: str) -> int:
        """Acknowledge processed jobs"""
        if not msg_ids:
            return 0
        return await self.redis.xack(stream_key, group_name, *msg_ids)

    async def aclose(self):
        await self.redis.close()
