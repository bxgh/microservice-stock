import asyncio
import logging
import os
import json
import traceback
from typing import Any

from gsd_shared.redis_protocol import (
    RedisStreamClient, TickJob, TickResult, JobStatus,
    STREAM_KEY_JOBS, STREAM_KEY_DATA, GROUP_MOOTDX_WORKERS, CONSUMER_PREFIX
)
from core.search_strategy import MatrixSearchStrategy
from core.realtime_strategy import RealtimeDeltaStrategy

logger = logging.getLogger("stream-worker")

class RedisStreamWorker:
    """
    负责从 Redis Stream 消费采集任务，并在内部调度 SearchStrategy 执行
    """
    def __init__(self, tdx_handler: Any):
        """
        Args:
            tdx_handler: MootdxHandler 实例，用于获取 TDX 连接池
        """
        self.tdx_handler = tdx_handler
        self.matrix_strategy = MatrixSearchStrategy()
        self.realtime_strategy = RealtimeDeltaStrategy()
        
        # Redis Config
        redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        redis_port = os.getenv("REDIS_PORT", 6379)
        redis_password = os.getenv("REDIS_PASSWORD", "")
        # DB 0 for stream (default)
        auth_part = f":{redis_password}@" if redis_password else ""
        redis_url = f"redis://{auth_part}{redis_host}:{redis_port}/0"
        is_cluster = os.getenv("REDIS_CLUSTER", "false").lower() == "true"
        
        self.redis_client = RedisStreamClient(redis_url, is_cluster=is_cluster)
        self.running = False
        
        # Unique consumer name: worker-{hostname}-{pid}
        hostname = os.getenv("HOSTNAME", "unknown")
        pid = os.getpid()
        self.consumer_name = f"{CONSUMER_PREFIX}-{hostname}-{pid}"
        
        # Concurrency Control
        self.concurrency = int(os.getenv("MOOTDX_CONCURRENCY", "10"))
        self.fetch_count = int(os.getenv("MOOTDX_FETCH_COUNT", "5"))
        
        logger.info(f"Worker Config: Concurrency={self.concurrency}, FetchCount={self.fetch_count}")
        self.sem = asyncio.Semaphore(self.concurrency)
        self._tasks = set()

    async def start(self):
        """启动 Worker"""
        logger.info(f"🚀 Starting Redis Stream Worker: {self.consumer_name}")
        
        # Ensure Consumer Group Exists
        await self.redis_client.init_consumer_group(STREAM_KEY_JOBS, GROUP_MOOTDX_WORKERS)
        
        self.running = True
        # Start the consumption loop as a background task
        loop_task = asyncio.create_task(self._consume_loop())
        self._tasks.add(loop_task)
        loop_task.add_done_callback(self._tasks.discard)

    async def stop(self):
        """停止 Worker"""
        logger.info(f"Stopping Redis Stream Worker (Pending tasks: {len(self._tasks)})...")
        self.running = False
        
        # Wait for all pending tasks to finish
        if self._tasks:
            logger.info(f"Waiting for {len(self._tasks)} tasks to complete...")
            await asyncio.gather(*self._tasks, return_exceptions=True)
            
        await self.redis_client.aclose()
        logger.info("Redis Stream Worker stopped.")

    async def _consume_loop(self):
        """主消费循环"""
        logger.info("Listening for jobs on stream...")
        
        while self.running:
            try:
                # 阻塞读取新消息 (XREADGROUP)
                # Count=5: 每次最多拉取 5 个任务
                # Block=2000: 阻塞 2秒
                streams = await self.redis_client.redis.xreadgroup(
                    groupname=GROUP_MOOTDX_WORKERS,
                    consumername=self.consumer_name,
                    streams={STREAM_KEY_JOBS: ">"},
                    count=self.fetch_count,
                    block=2000
                )
                
                if not streams:
                    continue
                    
                for stream_key, messages in streams:
                    for msg_id, msg_data in messages:
                        # 并发处理每个消息
                        task = asyncio.create_task(self._process_message(msg_id, msg_data))
                        self._tasks.add(task)
                        task.add_done_callback(self._tasks.discard)
                        
            except Exception as e:
                if self.running:
                    logger.error(f"Consume loop error: {e}")
                    await asyncio.sleep(1) # Prevent CPU spin

    async def _process_message(self, msg_id: str, msg_data: dict):
        """处理单条消息"""
        async with self.sem: # 限制并发数
            try:
                # 1. 解析任务
                try:
                    # Redis stream data is Dict[str, str]. Pydantic handles coercion.
                    job = TickJob(**msg_data)
                except Exception as e:
                    logger.error(f"❌ Invalid job format: {e}, Data: {msg_data}")
                    # 格式错误的任务直接 ACK 掉，否则会一直卡在 Pending
                    await self.redis_client.redis.xack(STREAM_KEY_JOBS, GROUP_MOOTDX_WORKERS, msg_id)
                    return

                logger.info(f"📥 Received Job: {job.stock_code} ({job.type}) [{msg_id}]")
                
                # 2. 执行策略
                result_status = JobStatus.FAILED
                data_blob = ""
                has_0925 = False
                err_msg = None
                row_count = 0
                
                try:
                    # 借用连接 (使用 acquire_client 以利用负载均衡)
                    async with self.tdx_handler.acquire_client() as client:
                        # 策略分发
                        if job.type == "intraday":
                             # 增量更新策略
                             records, has_0925 = await self.realtime_strategy.execute_intraday(client, job.stock_code, job.date)
                        else:
                             # 全量矩阵搜索策略 (Post-market)
                             records, has_0925 = await self.matrix_strategy.execute_post_market(client, job.stock_code, job.date)
                    
                    if records and len(records) > 0:
                        data_blob = json.dumps(records)
                        row_count = len(records)
                        result_status = JobStatus.SUCCESS
                        
                        if job.type != "intraday" and not has_0925:
                             # 仅对 Post-Market 任务标记 Partial (Intraday 不强求 09:25)
                             result_status = JobStatus.PARTIAL
                             err_msg = "Missing 09:25 data"
                    else:
                        result_status = JobStatus.FAILED
                        err_msg = "No data returned (Empty)"
                        
                except Exception as task_e:
                    logger.error(f"Task Execution Failed {job.stock_code}: {task_e}")
                    result_status = JobStatus.FAILED
                    err_msg = str(task_e)

                # 3. 推送结果
                result = TickResult(
                    job_id=job.job_id,
                    stock_code=job.stock_code,
                    date=job.date,
                    status=result_status,
                    row_count=row_count,
                    data_blob=data_blob,
                    check_0925=has_0925,
                    error_msg=err_msg
                )
                
                await self.redis_client.publish_result(result)
                
                # 4. 确认消息 (ACK)
                await self.redis_client.redis.xack(STREAM_KEY_JOBS, GROUP_MOOTDX_WORKERS, msg_id)
                
            except Exception as e:
                logger.error(f"Process message crash: {e}")

