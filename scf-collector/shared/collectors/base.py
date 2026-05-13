import abc
from typing import List, Dict, Any

from shared.utils.models import KLineModel

class BaseCollector(abc.ABC):
    """
    抽象数据采集器基类。
    所有具体的数据源适配器（如 AkShare, Tushare）都必须继承该类。
    """
    
    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """返回数据源的名称，例如 'akshare'"""
        pass

    @abc.abstractmethod
    async def fetch_daily_kline(self, ts_code: str, trade_date: str) -> List[KLineModel]:
        """
        获取日线 K 线数据。
        为了符合 Async First 规范，该方法必须是 async 的。
        如果底层的库是同步的（如 tushare），可以在子类中使用 asyncio.to_thread 包装。
        
        Args:
            ts_code: 股票代码，格式为 '000001.SZ'
            trade_date: 交易日期，格式为 'YYYY-MM-DD'
            
        Returns:
            返回 KLineModel 列表，每条记录字段如下:
            - ts_code: str (e.g. '000001.SZ')
            - trade_date: str (e.g. '2026-05-08')
            - open / high / low / close: float
            - pre_close: float
            - change: float
            - pct_chg: float (小数，如 0.05 代表 5%)
            - volume: float (成交量，单位: 手)
            - amount: float (成交额，单位: 元)
        """
        pass

    def normalize_data(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        [可选] 辅助方法，将原始数据结构转换为标准化的 List[Dict] 结构。
        子类可以选择性地重写此方法以集中处理字段映射和数据类型转换。
        """
        return raw_data
