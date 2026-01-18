from fastapi import APIRouter, Query, HTTPException, Path
from typing import Optional
from app.services.data_audit_service import data_audit_service
from app.models.data_audit import DataAuditResponse, DataAuditSummary, DataAuditDetailResponse

router = APIRouter()

@router.get("", response_model=DataAuditResponse)
async def list_data_audits(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    trade_date: Optional[str] = Query(None, description="交易日 YYYY-MM-DD"),
    data_type: Optional[str] = Query(None, description="数据类型"),
    level: Optional[str] = Query(None, description="告警级别")
):
    """
    查询数据审计汇总列表
    """
    try:
        return await data_audit_service.get_summaries(
            page=page, 
            size=size, 
            trade_date=trade_date,
            data_type=data_type,
            level=level
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{id}", response_model=DataAuditSummary)
async def get_data_audit_summary(
    id: int = Path(..., description="Audit Summary ID")
):
    """
    获取单个审计汇总详情
    """
    try:
        result = await data_audit_service.get_summary_by_id(id)
        if not result:
            raise HTTPException(status_code=404, detail="Audit summary not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{id}/details", response_model=DataAuditDetailResponse)
async def get_data_audit_details(
    id: int = Path(..., description="Audit Summary ID")
):
    """
    获取审计详情列表
    """
    try:
        # Check if exists first
        summary = await data_audit_service.get_summary_by_id(id)
        if not summary:
            raise HTTPException(status_code=404, detail="Audit summary not found")
            
        details = await data_audit_service.get_details(id)
        return {"items": details}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
