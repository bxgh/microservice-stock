"""频率限制器 - 控制问财API调用频率"""
import asyncio
import time
import logging
from collections import deque

logger = logging.getLogger("pywencai-api")


class RateLimiter:
    """
    滑动窗口频率限制器
    
    用于控制问财API的调用频率,避免触发反爬机制
    默认: 每60秒最多10次请求
    """
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        初始化限流器
        
        Args:
            max_requests: 窗口内最大请求数
            window_seconds: 滑动窗口大小(秒)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        获取请求许可
        
        Returns:
            True 如果获取成功,False 如果需要等待
        """
        async with self._lock:
            now = time.time()
            
            # 移除过期的请求记录
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            # 检查是否超过限制
            if len(self.requests) >= self.max_requests:
                return False
            
            # 记录新请求
            self.requests.append(now)
            return True
    
    async def wait_and_acquire(self) -> None:
        """等待直到可以获取许可"""
        while not await self.acquire():
            # 计算需要等待的时间
            async with self._lock:
                if self.requests:
                    wait_time = self.requests[0] + self.window_seconds - time.time()
                    if wait_time > 0:
                        logger.info(f"频率限制,等待 {wait_time:.1f} 秒")
                        await asyncio.sleep(min(wait_time + 0.1, 5))
                else:
                    await asyncio.sleep(1)
    
    def get_remaining(self) -> int:
        """获取剩余配额"""
        now = time.time()
        # 清理过期记录
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()
        return max(0, self.max_requests - len(self.requests))
