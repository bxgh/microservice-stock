from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException, Query
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("akshare-api.info")

@router.get("/information/analyst-ranks")
async def get_analyst_ranks(request: Request, date: Optional[str] = None):
    """获取机构评级数据"""
    service = request.app.state.akshare_service
    return await service.get_analyst_ranks(current_date=date)

@router.get("/information/forecasts")
async def get_forecasts(request: Request, period: str = Query(..., description="财报期 YYYY-MM-DD")):
    """获取业绩预告"""
    service = request.app.state.akshare_service
    return await service.get_performance_forecast(period_date=period)

@router.get("/information/sentiment/{code}")
async def get_sentiment(request: Request, code: str):
    """获取个股热度统计"""
    service = request.app.state.akshare_service
    return await service.get_sentiment_stats(symbol=code)
