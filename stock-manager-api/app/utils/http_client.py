import httpx
from typing import Dict, Any
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("stock-manager.http_client")

class ContainerClient:
    """容器间 HTTP 客户端"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.base_urls = {
            "baostock": settings.BAOSTOCK_API_URL,
            "akshare": settings.AKSHARE_API_URL,
            "pywencai": settings.PYWENCAI_API_URL
        }
    
    async def get(self, container: str, path: str, **kwargs) -> Dict[str, Any]:
        """发送 GET 请求"""
        base_url = self.base_urls.get(container)
        if not base_url:
            raise ValueError(f"Unknown container: {container}")
        
        url = f"{base_url}{path}"
        try:
            response = await self.client.get(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"GET {url} failed: {e}")
            raise
    
    async def post(self, container: str, path: str, **kwargs) -> Dict[str, Any]:
        """发送 POST 请求"""
        base_url = self.base_urls.get(container)
        if not base_url:
            raise ValueError(f"Unknown container: {container}")
        
        url = f"{base_url}{path}"
        try:
            response = await self.client.post(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"POST {url} failed: {e}")
            raise
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

# 全局客户端对象
http_client = ContainerClient()
