import uuid
from fastapi import APIRouter, HTTPException, Query, Request
from app.services.calendar_service import calendar_service
from typing import Dict, Any, List, Optional
import datetime

router = APIRouter()

def _error_response(code: str, message: str, request_id: str) -> dict:
    """生成符合项目规范的错误响应体"""
    return {"error": {"code": code, "message": message, "request_id": request_id}}

@router.get("/trading_days")
async def get_trading_days(
    request: Request,
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """获取指定日期范围内的交易日列表"""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])
    data = await calendar_service.get_trading_days(start_date, end_date)
    if data is None:
        raise HTTPException(
            status_code=500,
            detail=_error_response("CALENDAR_ERROR", "获取交易日列表失败", request_id)
        )
    return {"status": "success", "data": data}

@router.get("/is_open")
async def check_is_open(
    request: Request,
    date: Optional[str] = Query(None, description="检查日期 (YYYY-MM-DD)，默认为今日")
):
    """检查特定日期是否为交易日"""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])
    data = await calendar_service.is_trading_day(date)
    if data is None:
        raise HTTPException(
            status_code=500,
            detail=_error_response("CALENDAR_ERROR", f"检查交易日状态失败: {date}", request_id)
        )
    return data

@router.get("/recent")
async def get_recent_trading_days(
    request: Request,
    limit: int = Query(5, ge=1, le=100, description="获取最近几个交易日")
):
    """获取最近的 N 个交易日"""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])
    data = await calendar_service.get_recent_trading_days(limit)
    if data is None:
        raise HTTPException(
            status_code=500,
            detail=_error_response("CALENDAR_ERROR", "获取最近交易日失败", request_id)
        )
    return {"status": "success", "data": data}
