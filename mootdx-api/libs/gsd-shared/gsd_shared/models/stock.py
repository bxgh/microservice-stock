"""
股票信息数据模型
基于 services/get-stockdata/src/models/stock_models.py
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class StockCodeMapping(BaseModel):
    """股票代码映射信息 - 支持多数据源"""
    standard: str = Field(..., description="标准代码")
    tushare: str = Field(..., description="Tushare代码")
    akshare: str = Field(..., description="AKShare代码")
    tonghua_shun: str = Field(..., description="同花顺代码")
    wind: str = Field(..., description="Wind代码")
    east_money: str = Field(..., description="东方财富代码")


class StockInfo(BaseModel):
    """股票基础信息"""
    stock_code: str = Field(..., description="股票代码", json_schema_extra={"example": "000001"})
    stock_name: str = Field(..., description="股票名称", json_schema_extra={"example": "平安银行"})
    exchange: str = Field(..., description="交易所", pattern="^(SH|SZ|BJ)$")
    asset_type: str = Field("stock", description="资产类型")
    is_active: bool = Field(True, description="是否活跃")
    code_mappings: StockCodeMapping = Field(..., description="多格式代码映射")
    list_date: Optional[datetime] = Field(None, description="上市日期")
    delist_date: Optional[datetime] = Field(None, description="退市日期")
    industry: Optional[str] = Field(None, description="所属行业")
    sector: Optional[str] = Field(None, description="所属板块")
    market_cap: Optional[float] = Field(None, description="总市值(亿元)")
    
    model_config = {
        "populate_by_name": True
    }
