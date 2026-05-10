import logging
import asyncio
import httpx
from typing import Type, TypeVar, Optional, Dict, Any, Union
from pydantic import BaseModel, ValidationError

from gsd_shared.models.api.response import ApiResponse
from gsd_shared.exceptions import SchemaValidationError

T = TypeVar("T")
ModelT = TypeVar("ModelT", bound=BaseModel)

logger = logging.getLogger(__name__)

class BaseApiClient:
    """
    通用 API 客户端基类
    
    集成 Pydantic 模型自动校验与统一异常处理。
    """
    
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        
    async def close(self):
        await self.client.aclose()
        
    async def _get_with_retry(self, endpoint: str, params: Dict[str, Any] = None, retries: int = 3) -> Any:
        last_exception = None
        for attempt in range(retries):
            try:
                url = f"{self.base_url}/{endpoint.lstrip('/')}"
                resp = await self.client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_exception = e
                logger.warning(f"API attempt {attempt + 1} failed for {endpoint}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(1 * (attempt + 1)) # Exponential backoff
        
        logger.error(f"API request failed after {retries} attempts: {last_exception}")
        raise last_exception

    async def get_object(
        self, 
        endpoint: str, 
        response_model: Type[ApiResponse[ModelT]], 
        params: Dict[str, Any] = None
    ) -> Optional[ModelT]:
        """
        获取并校验单个对象
        """
        raw_data = await self._get_with_retry(endpoint, params)
        
        try:
            # 1. 顶层结构校验 (code, msg, success)
            api_resp = response_model.model_validate(raw_data)
            
            # 2. 业务结果校验
            if not api_resp.success or api_resp.code != 200:
                raise httpx.HTTPStatusError(
                    f"Business Error: {api_resp.message}", 
                    request=None, 
                    response=None
                )
                
            # 3. 数据非空校验 (视业务需求而定，这里假设 success=True data 应有值)
            if api_resp.data is None:
                 # 部分接口 success=True 但 data=None 是合法的 (如无数据)，需根据具体 Model 定义
                 pass
                 
            return api_resp.data
            
        except ValidationError as e:
            logger.error(f"Schema validation failed for {endpoint}: {e}")
            raise SchemaValidationError(f"Invalid response schema: {e}", raw_data)
