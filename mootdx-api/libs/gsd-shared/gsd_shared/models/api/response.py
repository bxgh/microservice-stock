from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    """
    统一 API 响应结构
    
    所有微服务接口应返回此结构的 JSON 数据。
    """
    code: int = Field(..., description="业务响应码 (200=成功)")
    message: str = Field(..., description="响应消息")
    data: Optional[T] = Field(None, description="业务数据 payload")
    success: bool = Field(..., description="是否成功标记")
    
    @classmethod
    def success_response(cls, data: T, message: str = "success") -> "ApiResponse[T]":
        return cls(code=200, message=message, data=data, success=True)
        
    @classmethod
    def error_response(cls, code: int, message: str) -> "ApiResponse[T]":
        return cls(code=code, message=message, data=None, success=False)


class TickRecord(BaseModel):
    """单条分笔数据记录"""
    time: str = Field(..., description="时间 (HH:MM:SS)")
    price: float = Field(..., description="价格")
    vol: int = Field(..., description="成交量 (手/股)")
    direction: int = Field(..., description="买卖方向 (0=中性, 1=买, 2=卖)")
    
    # 可选字段 (部分源可能不提供)
    buy_vol: Optional[int] = None
    sell_vol: Optional[int] = None


class TickDataResponse(BaseModel):
    """分笔数据响应 Payload"""
    symbol: str = Field(..., description="股票代码")
    date: str = Field(..., description="交易日期")
    count: int = Field(..., description="记录总数")
    ticks: List[TickRecord] = Field(..., description="分笔明细")


class KLineRecord(BaseModel):
    """单条K线记录"""
    date: str = Field(..., description="日期 (YYYY-MM-DD)")
    open: float
    close: float
    high: float
    low: float
    vol: float
    amount: float
    
class KLineDataResponse(BaseModel):
    """K线数据响应 Payload"""
    symbol: str
    period: str = Field(..., description="周期 (day/min)")
    count: int
    data: List[KLineRecord]
