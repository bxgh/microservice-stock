"""问财查询端点"""
import logging
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field

import pywencai

router = APIRouter()
logger = logging.getLogger("pywencai-api")

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒


class QueryRequest(BaseModel):
    """问财查询请求"""
    q: str = Field(..., description="查询语句,如'今日涨停'")
    perpage: int = Field(100, ge=1, le=100, description="每页数量")


@router.post("/query")
async def wencai_query(request: Request, body: QueryRequest):
    """
    问财自然语言选股
    
    ⚠️ 注意: 同花顺问财有反爬限制,约30%失败率
    
    - **q**: 查询语句,如 "今日涨停", "连续3日涨停", "PE小于20"
    - **perpage**: 返回数量
    """
    request_id = getattr(request.state, "request_id", "unknown")
    rate_limiter = request.app.state.rate_limiter
    
    # 等待获取频率配额
    await rate_limiter.wait_and_acquire()
    
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(
                f"问财查询: q='{body.q}', attempt={attempt + 1}/{MAX_RETRIES}",
                extra={"request_id": request_id}
            )
            
            # 使用 pywencai 查询
            df = pywencai.get(query=body.q, perpage=body.perpage)
            
            if df is None or (hasattr(df, 'empty') and df.empty):
                return {"columns": [], "data": []}
            
            # 转换为标准格式
            columns = df.columns.tolist()
            data = df.values.tolist()
            
            logger.info(
                f"问财查询成功: q='{body.q}', rows={len(data)}",
                extra={"request_id": request_id}
            )
            
            return {
                "columns": columns,
                "data": data,
            }
            
        except Exception as e:
            last_error = e
            error_msg = str(e)
            
            # 检查是否是验证码错误
            if "验证码" in error_msg or "captcha" in error_msg.lower():
                logger.warning(
                    f"问财验证码错误,重试 {attempt + 1}/{MAX_RETRIES}",
                    extra={"request_id": request_id}
                )
            else:
                logger.error(
                    f"问财查询失败: error={e}",
                    extra={"request_id": request_id}
                )
            
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
    
    # 所有重试都失败
    raise HTTPException(
        status_code=503,
        detail=f"问财服务暂时不可用 (重试{MAX_RETRIES}次后失败): {str(last_error)}"
    )


@router.get("/sector/hot")
async def get_hot_sectors(
    request: Request,
    limit: int = Query(20, ge=1, le=50, description="返回数量")
):
    """
    获取热门板块
    
    ⚠️ 注意: 同花顺问财有反爬限制
    """
    request_id = getattr(request.state, "request_id", "unknown")
    rate_limiter = request.app.state.rate_limiter
    
    # 等待获取频率配额
    await rate_limiter.wait_and_acquire()
    
    try:
        logger.info(f"获取热门板块: limit={limit}", extra={"request_id": request_id})
        
        # 使用问财查询热门板块
        df = pywencai.get(query="今日热门板块", perpage=limit)
        
        if df is None or (hasattr(df, 'empty') and df.empty):
            return []
        
        columns = df.columns.tolist()
        data = df.values.tolist()
        
        # 尝试提取结构化数据
        result = []
        for row in data:
            item = {}
            for i, col in enumerate(columns):
                if i < len(row):
                    item[col] = row[i]
            result.append(item)
        
        logger.info(f"获取热门板块成功: count={len(result)}", extra={"request_id": request_id})
        return result
        
    except Exception as e:
        logger.error(f"获取热门板块失败: error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=503, detail=f"问财服务暂时不可用: {str(e)}")
