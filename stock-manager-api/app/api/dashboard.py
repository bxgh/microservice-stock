from fastapi import APIRouter, HTTPException
from app.services.dashboard_service import DashboardService

router = APIRouter()
dashboard_service = DashboardService()

@router.get("/overview")
async def get_overview():
    """获取仪表盘概览"""
    try:
        return await dashboard_service.get_overview()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")
