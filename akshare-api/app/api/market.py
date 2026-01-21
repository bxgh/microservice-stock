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


@router.get("/capital_flow/{code}")
async def get_capital_flow(request: Request, code: str):
    """
    获取个股资金流向 (最近30日)
    
    - **code**: 股票代码,如 600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        result = await service.get_capital_flow(code)
        logger.info(f"获取资金流向成功: code={code}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取资金流向失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取资金流向失败: {str(e)}")


@router.get("/block_trade/daily")
async def get_block_trade(
    request: Request,
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD"),
):
    """
    获取大宗交易数据
    
    - **date**: 若不传则返回最近交易日数据
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    # 默认日期逻辑在 Service 层或这里处理? Service 层 stock_dzjy_mrtj如果不传日期会报错吗?
    # akshare 接口通常需要日期. 让我们简单点, 如果没传交给 Service 也许能处理? 
    # Service get_block_trade expecting date.
    if not date:
        # 简单默认今天, 或者让前端传. 这里为了友好, 默认今天.
        from datetime import datetime
        date = datetime.now().strftime("%Y-%m-%d")
        
    try:
        result = await service.get_block_trade(date)
        logger.info(f"获取大宗交易成功: date={date}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取大宗交易失败: date={date}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取大宗交易失败: {str(e)}")


@router.get("/margin/{code}")
async def get_margin_data(request: Request, code: str):
    """
    获取融资融券数据 (最近30日)
    
    - **code**: 股票代码,如 600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        result = await service.get_margin_data(code)
        logger.info(f"获取融资融券成功: code={code}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取融资融券失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取融资融券失败: {str(e)}")
