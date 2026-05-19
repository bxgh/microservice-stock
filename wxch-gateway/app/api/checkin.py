from fastapi import APIRouter, Depends, Query, Path
from typing import Optional
from app.models.checkin import (
    MaximQuoteCreate,
    MaximQuoteResponse,
    TodayQuoteResponse,
    MaximCheckinSubmit,
    MaximCheckinSubmitResponse,
    MaximActionRequest,
    MaximActionResponse,
    MaximTimelineResponse
)
from app.services.checkin_service import checkin_service
from app.utils.auth import get_current_user_id

router = APIRouter()

@router.post("/maxim/quote", response_model=MaximQuoteResponse, summary="手工录入投资格言")
async def create_quote(
    data: MaximQuoteCreate,
    user_id: int = Depends(get_current_user_id)
):
    """
    用户手工录入、复制粘贴投资格言接口。
    - 格言正文必须在 10-500 字之间。
    - 自动关联录入者。
    """
    res = await checkin_service.create_quote(user_id, data)
    return MaximQuoteResponse(data=res)

# --- 以下为后续 E23-S2 和 E23-S3 保留的 API 端点，返回 501 表示尚未实现或占位，不阻塞注册 ---

@router.get("/today", response_model=TodayQuoteResponse, summary="获取今日锁定待打卡格言")
async def get_today_quote(
    user_id: int = Depends(get_current_user_id)
):
    """获取或锁定今日分配的格言打卡任务，包含冷启动空库容错"""
    res = await checkin_service.get_or_lock_today_quote(user_id)
    return TodayQuoteResponse(data=res)

@router.post("/maxim/submit", response_model=MaximCheckinSubmitResponse, summary="提交格言打卡感悟")
async def submit_checkin(
    data: MaximCheckinSubmit,
    user_id: int = Depends(get_current_user_id)
):
    """提交打卡反思感悟，至少 30 字，并在同一事务中原子累加计数"""
    res = await checkin_service.submit_checkin(user_id, data)
    return MaximCheckinSubmitResponse(data=res)

@router.post("/maxim/action", response_model=MaximActionResponse, summary="操作格言状态")
async def update_action(
    data: MaximActionRequest,
    user_id: int = Depends(get_current_user_id)
):
    """更新动作：收藏（favorite）、跳过（skip）、永久屏蔽（dislike）"""
    await checkin_service.update_action(user_id, data)
    return MaximActionResponse()

@router.get("/maxim/timeline", response_model=MaximTimelineResponse, summary="获取单条格言的反思时间轴")
async def get_timeline(
    quote_id: int = Query(..., description="格言ID"),
    user_id: int = Depends(get_current_user_id)
):
    """获取单条格言下该用户历史提交的所有解读反思日记聚合列表"""
    res = await checkin_service.get_timeline(user_id, quote_id)
    return MaximTimelineResponse(data=res)
