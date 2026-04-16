from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class IndicatorItem(BaseModel):
    name: str
    value: float
    score: float

class MonitorSummary(BaseModel):
    trade_date: date
    total_score: float
    status: str
    indicators: List[IndicatorItem]

class HistoryPoint(BaseModel):
    trade_date: date
    value: float
