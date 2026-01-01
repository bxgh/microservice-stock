from fastapi import APIRouter, Query, HTTPException
from app.services.calendar_service import CalendarService
from app.services.baseline_service import BaselineService

router = APIRouter()
calendar_service = CalendarService()
baseline_service = BaselineService()

@router.get("/calendar/tradingDays")
async def get_trading_days(
    week: str = Query("current", description="week format: current or YYYY-Www")
):
    """获取交易日历"""
    try:
        return await calendar_service.get_trading_days(week)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")

@router.get("/baseline/current")
async def get_current_baseline():
    """获取当前标的基线"""
    try:
        return await baseline_service.get_current_baseline()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")
