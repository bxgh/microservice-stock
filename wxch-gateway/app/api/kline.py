from fastapi import APIRouter, Query, HTTPException
from app.models.kline import KlineResponse
from app.services.kline_service import kline_service
from typing import Optional

router = APIRouter()

@router.get("/{code}/kline", response_model=KlineResponse)
async def get_stock_kline(
    code: str,
    frequency: str = Query("d", pattern="^(d|w|m)$"),
    adjust: str = Query("3", pattern="^(1|2|3)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(500, ge=1, le=1000)
):
    """获取个股 K 线数据"""
    try:
        data = await kline_service.get_kline(
            code=code,
            frequency=frequency,
            adjust=adjust,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {
            "code": code,
            "frequency": frequency,
            "adjust": adjust,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
