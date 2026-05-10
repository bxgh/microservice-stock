"""
K线数据模型
基于 ClickHouse stock_kline_daily 表结构
"""

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


class KLineRecord(BaseModel):
    """
    K线数据记录 - 统一模型
    
    字段名与 ClickHouse 表保持一致
    提供 MySQL 数据转换方法
    """
    stock_code: str = Field(..., description="股票代码（6位）")
    trade_date: date = Field(..., description="交易日期")
    open_price: float = Field(..., description="开盘价")
    high_price: float = Field(..., description="最高价")
    low_price: float = Field(..., description="最低价")
    close_price: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量（股）")
    amount: float = Field(..., description="成交额（元）")
    turnover_rate: Optional[float] = Field(None, description="换手率（%）")
    change_pct: Optional[float] = Field(None, description="涨跌幅（%）")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "stock_code": "600519",
                "trade_date": "2023-01-01",
                "open_price": 1700.0,
                "close_price": 1750.0
            }
        }
    }
    
    @classmethod
    def from_mysql(cls, row: dict) -> "KLineRecord":
        """
        从 MySQL 行数据创建实例（字段名映射）
        
        MySQL 字段: code, trade_date, open, high, low, close, volume, amount, turnover, pct_chg
        ClickHouse/模型字段: stock_code, trade_date, open_price, ..., turnover_rate, change_pct
        
        Args:
            row: MySQL查询返回的字典
            
        Returns:
            KLineRecord 实例
        """
        return cls(
            stock_code=row['code'],
            trade_date=row['trade_date'],
            open_price=row['open'],
            high_price=row['high'],
            low_price=row['low'],
            close_price=row['close'],
            volume=row['volume'],
            amount=row['amount'],
            turnover_rate=row.get('turnover'),
            change_pct=row.get('pct_chg')
        )
    
    def to_clickhouse_dict(self) -> dict:
        """
        转换为 ClickHouse 插入所需的字典
        
        Returns:
            字典格式数据
        """
        return {
            'stock_code': self.stock_code,
            'trade_date': self.trade_date,
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'close_price': self.close_price,
            'volume': self.volume,
            'amount': self.amount,
            'turnover_rate': self.turnover_rate,
            'change_pct': self.change_pct
        }
