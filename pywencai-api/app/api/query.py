"""问财查询端点"""
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("pywencai-api.api.query")


class QueryRequest(BaseModel):
    """问财查询请求"""
    q: str = Field(..., description="查询语句,如'今日涨停'")
    perpage: int = Field(100, ge=1, le=200, description="每页数量")
    loop: bool = Field(False, description="是否循环分页获取全部结果")


@router.post("/query")
async def wencai_query(request: Request, body: QueryRequest):
    """
    问财自然语言选股
    
    ⚠️ 注意: 同花顺问财有反爬限制,由 Service 处理重试与频率控制
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.wencai_service
    
    try:
        result = await service.query(q=body.q, perpage=body.perpage, loop=body.loop)
        logger.info(f"问财查询成功: q='{body.q}', rows={len(result.get('data', []))}", extra={"request_id": request_id})
        return result
    
    except ValueError as e:
        logger.warning(f"查询参数无效: q='{body.q}', error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=400, detail="查询参数无效")
    
    except TimeoutError:
        logger.error(f"查询超时: q='{body.q}'", extra={"request_id": request_id})
        raise HTTPException(status_code=504, detail="服务响应超时，请稍后重试")
        
    except Exception as e:
        error_msg = str(e).lower()
        # 检测验证码或反爬触发
        if "验证码" in error_msg or "captcha" in error_msg:
            logger.warning(f"触发反爬验证: q='{body.q}'", extra={"request_id": request_id})
            raise HTTPException(status_code=503, detail="服务暂时不可用，触发反爬验证")
        
        logger.error(f"问财查询失败: q='{body.q}', error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=503, detail="问财服务暂时不可用")


@router.get("/sector/hot")
async def get_hot_sectors(
    request: Request,
    limit: int = Query(20, ge=1, le=50, description="返回数量")
):
    """
    获取热门板块
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.wencai_service
    
    try:
        result = await service.get_hot_sectors(limit)
        logger.info(f"获取热门板块成功: count={len(result)}", extra={"request_id": request_id})
        return result
        
    except Exception as e:
        logger.error(f"获取热门板块失败: error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=503, detail=f"问财服务暂时不可用: {str(e)}")
