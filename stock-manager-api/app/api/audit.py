from fastapi import APIRouter, Query, HTTPException
from app.services.audit_service import AuditService

router = APIRouter()
audit_service = AuditService()

@router.get("/weekly")
async def get_audit_weekly(
    week: str = Query("current", description="week format: current or YYYY-Www")
):
    """获取周度审计报告"""
    try:
        return await audit_service.get_audit_weekly(week)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")

@router.get("/gate")
async def get_gate_audits(
    date: str = Query(None, description="交易日 YYYY-MM-DD"),
    limit: int = Query(20, description="返回条数")
):
    """获取数据闸门(Data Gate)审计记录"""
    try:
        return await audit_service.get_gate_audits(trade_date=date, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")
