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
@router.post("/remediate")
async def remediate_data(
    date: str,
    data_type: str = "kline",
    scope: str = "incremental"
):
    """触发指定日期的数据补偿 (运维补数)
    
    Args:
        date: 要修复的日期 YYYY-MM-DD
        data_type: 数据类型: kline
        scope: 范围: incremental (补缺) / full (重跑)
    """
    try:
        return await ops_service.remediate_data(date, data_type, scope)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")

@router.get("/reject-report")
async def get_reject_report(date: str = None):
    """获取数据校验拒绝报告
    
    Args:
        date: 日期 YYYY-MM-DD，不传则默认今天
    """
    try:
        return await ops_service.get_reject_report(date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")
