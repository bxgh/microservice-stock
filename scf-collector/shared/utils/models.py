from pydantic import BaseModel, Field
from typing import Optional

class KLineModel(BaseModel):
    """
    标准 K 线数据契约 (对齐 Tushare 口径)
    """
    ts_code: str = Field(..., description="股票代码 (如 600519.SH)")
    trade_date: str = Field(..., description="交易日期 (YYYY-MM-DD)")
    open: float = Field(0.0)
    high: float = Field(0.0)
    low: float = Field(0.0)
    close: float = Field(0.0)
    pre_close: float = Field(0.0, description="昨收价")
    change: float = Field(0.0, description="价格变动")
    pct_chg: float = Field(0.0, description="涨跌幅 (小数, 如 0.05 代表 5%)")
    volume: float = Field(0.0, description="成交量 (单位: 手)")
    amount: float = Field(0.0, description="成交额 (单位: 元)")

    class Config:
        from_attributes = True
