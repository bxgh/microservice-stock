from fastapi import APIRouter, HTTPException
from app.services.ops_service import OpsService

router = APIRouter()
ops_service = OpsService()

@router.get("/freshness")
async def get_sync_freshness():
    """获取数据时效性"""
    try:
        return await ops_service.get_sync_freshness()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")

@router.get("/adjust-factor")
async def get_adjust_factor_by_date(date: str = None):
    """获取指定日期的复权因子数据
    
    Args:
        date: 日期，格式 YYYY-MM-DD，不传则默认今天
    """
    try:
        return await ops_service.get_adjust_factor_by_date(date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")
