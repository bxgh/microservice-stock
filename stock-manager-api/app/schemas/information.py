from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator
from app.utils.code_utils import normalize_ts_code

# --- Analyst Rank ---


class AnalystRankBase(BaseModel):
    ts_code: str = Field(..., alias="stock_code")
    report_date: date
    analyst: str
    rating: str
    change_direction: Optional[str] = None
    target_price: Optional[float] = None

    @field_validator("ts_code", mode="before")
    @classmethod
    def validate_ts_code(cls, v: str) -> str:
        return normalize_ts_code(v)

    class Config:
        populate_by_name = True


class AnalystRankCreate(AnalystRankBase):
    pass


class AnalystRankResponse(AnalystRankBase):
    id: int
    created_at: Optional[datetime] = None

# --- Performance Forecast ---


class PerformanceForecastBase(BaseModel):
    ts_code: str = Field(..., alias="stock_code")
    notice_date: date
    report_period: date
    type: Optional[str] = None
    growth_min: Optional[float] = None
    growth_max: Optional[float] = None

    @field_validator("ts_code", mode="before")
    @classmethod
    def validate_ts_code(cls, v: str) -> str:
        return normalize_ts_code(v)

    class Config:
        populate_by_name = True


class PerformanceForecastCreate(PerformanceForecastBase):
    pass


class PerformanceForecastResponse(PerformanceForecastBase):
    id: int

# --- Sentiment Daily ---


class SentimentDailyBase(BaseModel):
    ts_code: str = Field(..., alias="stock_code")
    trade_date: date
    post_count: int = 0
    read_count: int = 0
    comment_count: int = 0
    rank_score: Optional[int] = 0

    @field_validator("ts_code", mode="before")
    @classmethod
    def validate_ts_code(cls, v: str) -> str:
        return normalize_ts_code(v)

    class Config:
        populate_by_name = True


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
