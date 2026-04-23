from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class BidAskItem(BaseModel):
    """单档买卖盘数据"""
    price: float
    volume: float

class BidAsk(BaseModel):
    """五档买卖盘"""
    buy: List[BidAskItem] = Field(..., description="买1-买5")
    sell: List[BidAskItem] = Field(..., description="卖1-卖5")

class QuoteBase(BaseModel):
    """行情基础数据"""
    code: str
    name: str
    last: float = Field(..., description="最新价")
    open: float
    high: float
    low: float
    prev_close: float = Field(..., description="昨收价")
    chg: float = Field(..., description="涨跌额")
    chg_pct: float = Field(..., description="涨跌幅(%)")
    volume: float = Field(..., description="成交量(手)")
    amount: float = Field(..., description="成交额(元)")
    timestamp: int = Field(..., description="数据时间戳")

class SpotResponse(BaseModel):
    """实时行情响应"""
    data: QuoteBase

class SnapshotData(QuoteBase):
    """快照行情数据 (包含盘口)"""
    bid_ask: BidAsk
    pe_dynamic: Optional[float] = None
    pb: Optional[float] = None
    market_cap: Optional[float] = None
    float_market_cap: Optional[float] = None
    turnover_rate: Optional[float] = Field(None, description="换手率(%)")
    turnover_real: Optional[float] = Field(None, description="换手(实)(%)")
    quantity_ratio: Optional[float] = Field(None, description="量比")

class SnapshotResponse(BaseModel):
    """快照行情响应"""
    data: SnapshotData

class TimeSharePoint(BaseModel):
    """分时数据点"""
    time: str = Field(..., description="时间 (HHMM)")
    price: float = Field(..., description="当前价格")
    avg_price: Optional[float] = Field(None, description="均价")
    volume: float = Field(..., description="成交量 (当前分钟)")
    amount: float = Field(..., description="成交额 (当前分钟)")

class TimeShareResponse(BaseModel):
    """分时行情响应"""
    code: str
    turnover_rate: Optional[float] = Field(None, description="今日换手率(%)")
    turnover_real: Optional[float] = Field(None, description="今日换手(实)(%)")
    quantity_ratio: Optional[float] = Field(None, description="今日量比")
    data: List[TimeSharePoint]
