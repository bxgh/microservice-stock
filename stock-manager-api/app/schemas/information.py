from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel

# --- Analyst Rank ---
class AnalystRankBase(BaseModel):
    stock_code: str
    report_date: date
    analyst: str
    rating: str
    change_direction: Optional[str] = None
    target_price: Optional[float] = None

class AnalystRankCreate(AnalystRankBase):
    pass

class AnalystRankResponse(AnalystRankBase):
    id: int
    created_at: Optional[datetime] = None

# --- Performance Forecast ---
class PerformanceForecastBase(BaseModel):
    stock_code: str
    notice_date: date
    report_period: date
    type: Optional[str] = None
    growth_min: Optional[float] = None
    growth_max: Optional[float] = None

class PerformanceForecastCreate(PerformanceForecastBase):
    pass

class PerformanceForecastResponse(PerformanceForecastBase):
    id: int

# --- Sentiment Daily ---
class SentimentDailyBase(BaseModel):
    stock_code: str
    trade_date: date
    post_count: int = 0
    read_count: int = 0
    comment_count: int = 0
    rank_score: Optional[int] = 0

class SentimentDailyCreate(SentimentDailyBase):
    pass

class SentimentDailyResponse(SentimentDailyBase):
    id: int

# --- Common Responses ---
class SyncResult(BaseModel):
    total: int
    success: int
    failed: Optional[int] = 0
    message: Optional[str] = None
