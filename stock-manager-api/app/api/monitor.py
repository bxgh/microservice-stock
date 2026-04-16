from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.services.monitor_service import MonitorService
from app.schemas.monitor import MonitorSummary, HistoryPoint

router = APIRouter()
monitor_service = MonitorService()

@router.get("/summary", response_model=MonitorSummary)
async def get_monitor_summary():
    """获取结构性牛市监控最新概览数据"""
    summary = await monitor_service.get_summary()
    if not summary:
        raise HTTPException(status_code=404, detail="Monitor data not found")
    return summary

@router.get("/history/score", response_model=List[HistoryPoint])
async def get_score_history(
    limit: int = Query(90, description="返回的历史天数", ge=1, le=500)
):
    """获取健康分历史趋势数据 (默认 90 天)"""
    return await monitor_service.get_score_history(limit)

@router.get("/history/indicator/{name}", response_model=List[HistoryPoint])
async def get_indicator_history(
    name: str,
    limit: int = Query(90, description="返回的历史天数", ge=1, le=500)
):
    """获取单个指标的历史趋势数据 (默认 90 天)"""
    return await monitor_service.get_indicator_history(name, limit)
