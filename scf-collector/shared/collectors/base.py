import abc
from typing import List, Dict, Any

class BaseCollector(abc.ABC):
    """
    抽象数据采集器基类。
    所有具体的数据源适配器（如 AkShare, Tushare, mootdx）都必须继承该类。
    """
    
    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """返回数据源的名称，例如 'akshare'"""
        pass

    @abc.abstractmethod
    async def fetch_daily_kline(self, ts_code: str, trade_date: str) -> List[Dict[str, Any]]:
        """
        获取日线 K 线数据。
        为了符合 Async First 规范，该方法必须是 async 的。
        如果底层的库是同步的（如 tushare），可以在子类中使用 asyncio.to_thread 包装。
        
        Args:
            ts_code: 股票代码，格式为 '000001.SZ'
            trade_date: 交易日期，格式为 'YYYY-MM-DD'
            
        Returns:
            返回一个字典列表，每个字典代表一条符合 `stock_kline_daily` schema 的记录。
            要求的标准化字段:
            - ts_code: str (e.g. '000001.SZ')
            - trade_date: str (e.g. '2026-05-08')
            - open: float
            - high: float
            - low: float
            - close: float
            - pre_close: float
            - change: float
            - pct_chg: float (必须是小数，如 0.05 代表 5%)
            - vol: float (成交量)
            - amount: float (成交额，必须是元)
        """
        pass

    def normalize_data(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        [可选] 辅助方法，将原始数据结构转换为标准化的 List[Dict] 结构。
        子类可以选择性地重写此方法以集中处理字段映射和数据类型转换。
        """
        return raw_data
