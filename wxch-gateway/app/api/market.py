from fastapi import APIRouter, HTTPException, Query
from app.services.market_service import market_service
from typing import Dict, Any, List

router = APIRouter()

@router.get("/overview/latest")
async def get_latest_market_overview():
    """获取最新的全市场行情纵览 (ADS L1)"""
    data = await market_service.get_latest_overview()
    if not data:
        raise HTTPException(status_code=404, detail="未找到市场概览数据")
    return data

@router.get("/overview/history")
async def get_market_overview_history(
    limit: int = Query(20, description="返回的历史记录条数", ge=1, le=100)
):
    """获取全市场行情纵览历史"""
    data = await market_service.get_overview_history(limit)
    return data

@router.get("/structural/latest")
async def get_latest_structural_analysis():
    """获取最新的结构分化与行业旋转分析 (Chapter 2)"""
    data = await market_service.get_latest_structural()
    if not data:
        raise HTTPException(status_code=404, detail="未找到结构分析数据")
    return data
