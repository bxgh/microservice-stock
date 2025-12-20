"""市场数据相关端点"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("akshare-api.api.market")


@router.get("/dragon_tiger/daily")
async def get_dragon_tiger_daily(
    request: Request,
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD,默认最近交易日"),
):
    """
    获取龙虎榜数据
    
    - **date**: 交易日期,如 2024-01-15
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        result = await service.get_lhb_detail(date, date)
        logger.info(f"获取龙虎榜成功: date={date}, count={len(result)}", extra={"request_id": request_id})
        return result
        
    except Exception as e:
        logger.error(f"获取龙虎榜失败: date={date}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取龙虎榜失败: {str(e)}")


@router.get("/industry/stock/{code}")
async def get_stock_industry(request: Request, code: str):
    """
    获取个股所属行业
    
    - **code**: 股票代码,如 600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        info = await service.get_individual_info(code)
        
        if not info:
            raise HTTPException(status_code=404, detail=f"未找到股票: {code}")
        
        info["code"] = code
        logger.info(f"获取行业信息成功: code={code}", extra={"request_id": request_id})
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取行业信息失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取行业信息失败: {str(e)}")


@router.get("/rank/hot")
async def get_hot_rank(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="返回数量,默认50"),
):
    """
    获取热门股票排行
    
    - **limit**: 返回数量,最大100
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        result = await service.get_hot_rank(limit)
        
        # 补全 rank
        for i, item in enumerate(result):
            item["rank"] = i + 1
            
        logger.info(f"获取热门排行成功: limit={limit}, count={len(result)}", extra={"request_id": request_id})
        return result
        
    except Exception as e:
        logger.error(f"获取热门排行失败: error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取热门排行失败: {str(e)}")
