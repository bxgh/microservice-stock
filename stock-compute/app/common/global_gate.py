import time
import asyncio
from contextlib import asynccontextmanager
from app.utils.logger import get_logger

logger = get_logger("stock-compute.gate")

class GlobalTaskGate:
    """整个内网计算节点同时只允许 1 个重任务运行 (E3)"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.GATE_KEY = "task_gate:heavy"

    @asynccontextmanager
    async def heavy_task(self, task_id: str, timeout: int = 3600):
        # 简单实现：使用 Redis SET NX
        acquired = False
        start_wait = time.time()
        
        while time.time() - start_wait < 3600:  # 最多等待 1 小时
            # try to acquire
            res = await self.redis.set(self.GATE_KEY, task_id, ex=timeout, nx=True)
            if res:
                acquired = True
                break
            await asyncio.sleep(5)
            
        if not acquired:
            raise TimeoutError(f"{task_id} 等待全局闸门超时")

        start_exec = time.time()
        try:
            logger.info(f"[gate] {task_id} 获得执行权")
            yield
        finally:
            # 释放锁，确保只释放自己的锁
            current_val = await self.redis.get(self.GATE_KEY)
            if current_val == task_id.encode() or current_val == task_id:
                await self.redis.delete(self.GATE_KEY)
            logger.info(f"[gate] {task_id} 释放执行权, 耗时 {time.time()-start_exec:.1f}s")
