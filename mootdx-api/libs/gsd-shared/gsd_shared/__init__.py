"""
GSD-Shared: 股票数据平台共享库

提供统一的数据模型、常量和工具函数供 gsd-api 和 gsd-worker 使用。
"""

__version__ = "0.1.0"

from .models.kline import KLineRecord
from .models.stock import StockInfo, StockCodeMapping
from .models.sync import SyncStatus, SyncRecord
from .models.sync import SyncStatus, SyncRecord

__all__ = [
    "KLineRecord",
    "StockInfo", 
    "StockCodeMapping",
    "SyncStatus",
    "SyncRecord",
    "SyncRecord",
]
