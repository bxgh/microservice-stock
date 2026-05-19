from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

class MaximQuoteCreate(BaseModel):
    """手工录入格言请求模型"""
    content: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="格言正文，必须在10-500字之间"
    )
    source_author: Optional[str] = Field(
        default=None,
        max_length=64,
        description="格言作者"
    )
    source_book: Optional[str] = Field(
        default=None,
        max_length=128,
        description="来源书籍/媒体渠道"
    )
    category: int = Field(
        default=1,
        description="1=经典名言, 2=大佬语录, 3=历史教训, 4=用户摘录, 5=自己写的金句"
    )
    base_weight: int = Field(
        default=50,
        ge=1,
        le=100,
        description="基础权重(1-100)"
    )

class MaximQuoteResponseData(BaseModel):
    """格言创建响应数据模型"""
    quote_id: int
    content: str
    created_at: datetime

class MaximQuoteResponse(BaseModel):
    """格言创建完整响应模型"""
    code: int = 200
    message: str = "success"
    data: MaximQuoteResponseData

# --- 以下为后续 Story 保留/预留的模型，方便一次性对齐 ---

class HistoryInsight(BaseModel):
    """历史见解概要"""
    last_insight_content: Optional[str] = None
    last_insight_date: Optional[date] = None

class TodayQuoteDetail(BaseModel):
    """今日格言详情数据"""
    id: int
    content: str
    source_author: Optional[str] = None
    source_book: Optional[str] = None
    category: int
    is_favorited: int
    history_insight: Optional[HistoryInsight] = None

class TodayQuoteResponseData(BaseModel):
    """今日格言拉取响应数据"""
    business_date: date
    checkin_type: int = 2
    status: int = 0
    quote: Optional[TodayQuoteDetail] = None
    msg: Optional[str] = None

class TodayQuoteResponse(BaseModel):
    """今日格言拉取完整响应模型"""
    code: int = 200
    message: str = "success"
    data: TodayQuoteResponseData

class MaximCheckinSubmit(BaseModel):
    """格言打卡提交请求"""
    quote_id: int
    insight: str = Field(..., min_length=30, max_length=500, description="个人见解/反思感悟，至少30字")
    mood: Optional[int] = Field(None, description="情绪标记")

class MaximCheckinSubmitResponseData(BaseModel):
    """格言打卡提交响应数据"""
    diary_id: int
    title: str
    entry_date: date
    accumulated_insight_count: int

class MaximCheckinSubmitResponse(BaseModel):
    """格言打卡提交完整响应"""
    code: int = 200
    message: str = "success"
    data: MaximCheckinSubmitResponseData

class MaximActionRequest(BaseModel):
    """格言收藏、屏蔽、跳过请求"""
    quote_id: int
    action_type: str = Field(..., description="favorite=收藏, dislike=屏蔽, skip=跳过")
    value: int = Field(..., description="1=开启/跳过, 0=关闭")

class MaximActionResponse(BaseModel):
    """动作响应"""
    code: int = 200
    message: str = "success"

class TimelineItem(BaseModel):
    """时间轴见解记录"""
    diary_id: int
    date: date
    insight: str
    mood: Optional[int] = None
    market_summary: Optional[Dict[str, Any]] = None

class MaximTimelineResponseData(BaseModel):
    """见解时间轴响应数据"""
    quote_id: int
    content: str
    total_insights: int
    timeline: List[TimelineItem]

class MaximTimelineResponse(BaseModel):
    """见解时间轴完整响应"""
    code: int = 200
    message: str = "success"
    data: MaximTimelineResponseData
