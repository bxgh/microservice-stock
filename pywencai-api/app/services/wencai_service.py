import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
import pywencai
from app.utils.logger import get_logger

logger = get_logger("pywencai-api.service")

class WencaiService:
    """问财数据服务封装 - 包含频率限制与重试
    
    使用 asyncio.Semaphore 实现请求频率限制 (默认 10次/分钟)。
    内置重试机制，最多重试 3 次，延迟 5 秒。
    """
    
    def __init__(self, max_requests: int = 10, window: int = 60):
        self.semaphore = asyncio.Semaphore(max_requests)
        self.window = window
        self.max_retries = 3
        self.retry_delay = 5  # 秒

    async def _acquire_quota(self):
        """获取请求配额"""
        await self.semaphore.acquire()
        # 异步释放配额
        asyncio.create_task(self._release_after_delay())

    async def _release_after_delay(self):
        """延迟释放信号量"""
        await asyncio.sleep(self.window)
        self.semaphore.release()

    async def query(self, q: str, perpage: int = 100) -> Dict[str, Any]:
        """执行问财查询，带重试机制
        
        Args:
            q: 自然语言查询语句，如 "今日涨停"
            perpage: 每页返回数量
            
        Returns:
            查询结果字典，包含 columns 和 data 字段
            
        Raises:
            Exception: 当所有重试都失败时抛出
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            # 获取频率限制配额
            await self._acquire_quota()
            
            try:
                logger.info(f"正在执行问财查询: q='{q}', attempt={attempt+1}")
                
                # 使用 to_thread 执行同步阻塞调用
                df = await asyncio.to_thread(pywencai.get, query=q, perpage=perpage)
                
                if df is None or (hasattr(df, 'empty') and df.empty):
                    return {"columns": [], "data": []}
                
                return {
                    "columns": df.columns.tolist(),
                    "data": df.values.tolist(),
                }
            except Exception as e:
                last_error = e
                msg = str(e).lower()
                if "验证码" in msg or "captcha" in msg:
                    logger.warning(f"触发验证码，尝试重试: {attempt+1}/{self.max_retries}")
                else:
                    logger.error(f"问财查询异常: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    
        raise Exception(f"问财服务重试 {self.max_retries} 次后失败: {last_error}")

    async def get_hot_sectors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取热门板块
        
        Args:
            limit: 返回数量限制
            
        Returns:
            热门板块列表，每条记录包含板块相关信息
        """
        try:
            res = await self.query(q="今日热门板块", perpage=limit)
            columns = res.get("columns", [])
            data = res.get("data", [])
            
            result = []
            for row in data:
                item = {}
                for i, col in enumerate(columns):
                    if i < len(row):
                        item[col] = row[i]
                result.append(item)
            return result
        except Exception as e:
            logger.error(f"获取热门板块失败: {e}")
            return []
