from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

class StockInfo(BaseModel):
    ts_code: str
    name: Optional[str] = None
    market: Optional[str] = None
    industry_sw: Optional[str] = None


class TagInfo(BaseModel):
    id: int
    name: str
    category: int
    color: Optional[str] = None


class DiaryEntryCreate(BaseModel):
    entry_date: date
    entry_type: int = Field(
        default=5, 
        description="1=盘前 2=盘中 3=盘后 4=周复盘 5=随笔 6=个股研究"
    )
    mood: Optional[int] = Field(
        default=None, 
        description="情绪 1=冷静 2=兴奋 3=焦虑 4=恐惧 5=贪婪 6=困惑"
    )
    title: Optional[str] = None
    content: str
    content_format: str = "md_v1"
    visibility: int = Field(default=0, description="0=私密 1=链接可见 2=公开")
    is_pinned: bool = False
    stocks: List[str] = Field(
        default_factory=list, 
        description="List of ts_codes"
    )
    tags: List[str] = Field(
        default_factory=list, 
        description="List of tag names"
    )


class DiaryEntryUpdate(BaseModel):
    entry_type: Optional[int] = None
    mood: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    visibility: Optional[int] = None
    is_pinned: Optional[bool] = None
    stocks: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class DiaryEntryResponse(BaseModel):
    id: int
    user_id: int
    entry_date: date
    entry_type: int
    mood: Optional[int] = None
    title: Optional[str] = None
    content: str
    excerpt: Optional[str] = None
    word_count: int
    visibility: int
    is_pinned: bool
    mp_published_count: int
    created_at: datetime
    updated_at: datetime
    stocks: List[StockInfo] = []
    tags: List[TagInfo] = []


class DiaryEntryListResponse(BaseModel):
    id: int
    entry_date: date
    entry_type: int
    mood: Optional[int] = None
    title: Optional[str] = None
    excerpt: Optional[str] = None
    word_count: int
    is_pinned: bool
    mp_published_count: int
    created_at: datetime
    updated_at: datetime
    stocks: List[StockInfo] = []
    tags: List[TagInfo] = []


class PaginatedDiaryResponse(BaseModel):
    items: List[DiaryEntryListResponse]
    total: int
    page: int
    size: int


class MoodStat(BaseModel):
    mood: int
    count: int


class DiaryStatsResponse(BaseModel):
    monthly_days: int = Field(0, description="本月记录天数")
    error_book_count: int = Field(0, description="错题本总数")
    latest_mood: Optional[int] = Field(None, description="最近一次心情 ID")
    mood_distribution: List[MoodStat] = Field(
        default_factory=list, 
        description="心情分布统计"
    )


class DiaryPublishMPRequest(BaseModel):
    entry_id: int
    is_snapshot: bool = True


class DiaryPublishMPResponse(BaseModel):
    publish_record_id: int
    wx_media_id: Optional[str] = None
    message: str = "success"
