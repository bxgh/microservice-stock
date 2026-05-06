# 代码模板与规范

> **用途**: AI 生成代码时的标准模板

## 1. 新端点模板

```python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2026 Microservice Stock. All rights reserved.
FileName: endpoint_template.py
Description: 标准端点模板
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("service-name.api.module")

@router.get("/endpoint/{code}")
async def get_data(
    request: Request,
    code: str,
    param: Optional[str] = Query(None, description="参数说明"),
):
    """
    端点说明
    
    - **code**: 股票代码,如 600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.your_service
    
    try:
        result = await service.get_data(code)
        
        if not result:
            raise HTTPException(status_code=404, detail="未找到数据")
        
        logger.info(f"获取数据成功: code={code}", extra={"request_id": request_id})
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")
```

---

## 2. 服务层模板

```python
"""服务层"""
import asyncio
from app.utils.logger import get_logger

logger = get_logger("service-name.services.module")


class YourService:
    """服务类"""
    
    def __init__(self):
        self.lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """初始化"""
        if self._initialized:
            return
        # 初始化逻辑
        self._initialized = True
        logger.info("服务初始化完成")
    
    async def close(self):
        """清理资源"""
        # 清理逻辑
        self._initialized = False
        logger.info("服务已关闭")
    
    async def get_data(self, code: str):
        """获取数据"""
        async with self.lock:
            try:
                # 业务逻辑
                return {"code": code, "data": []}
            except Exception as e:
                logger.error(f"获取数据失败: {e}")
                raise
```

---

## 3. 错误响应格式

```python
# 标准错误响应
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid stock code format",
        "request_id": "a1b2c3d4"
    }
}
```

---

## 4. 日志规范

```python
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 必须包含 request_id
logger.info("操作成功", extra={"request_id": request_id})
logger.error(f"操作失败: {error}", extra={"request_id": request_id})
```

---

## 5. 资源管理

```python
# 必须使用 try...finally
async def fetch_data():
    client = None
    try:
        client = await create_connection()
        return await client.query()
    finally:
        if client:
            await client.close()

# 或使用上下文管理器
async with create_connection() as client:
    return await client.query()
```

---
> **最后更新**: 2026-01-07
