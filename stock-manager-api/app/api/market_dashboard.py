from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.market_query_service import MarketQueryService

router = APIRouter()
market_query_service = MarketQueryService()

@router.get("/l1")
async def get_l1_overview(date: Optional[str] = Query(None, description="日期 YYYY-MM-DD")):
    """获取 L1 市场全景数据"""
    try:
        data = await market_query_service.get_l1_overview(date)
        if not data:
            raise HTTPException(status_code=404, detail="No data found for the given date")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
