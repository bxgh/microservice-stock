from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class KlineItem(BaseModel):
    """单条 K 线数据"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    turnover: Optional[float] = None

class KlineResponse(BaseModel):
    """K 线接口响应"""
    code: str
    frequency: str
    adjust: str
    data: List[KlineItem]
