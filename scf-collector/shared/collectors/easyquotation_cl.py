import asyncio
import logging
import pandas as pd
from typing import List, Dict, Any
from .base import BaseCollector

logger = logging.getLogger(__name__)

class EasyQuotationCollector(BaseCollector):
    @property
    def source_name(self) -> str:
        return "easyquotation"

    def _convert_symbol(self, ts_code: str) -> str:
        """将 '600519.SH' 转换为 '600519'"""
        return ts_code.split('.')[0]

    def _fetch_sync(self, symbol: str) -> Dict[str, Any]:
        """同步方法：调用 easyquotation 获取实时行情"""
        import easyquotation
        try:
            # 切换到新浪源，键名更规范 (ASCII)
            quotation = easyquotation.use('sina')
            data = quotation.real([symbol])
            return data.get(symbol, {})
        except Exception as e:
            logger.error(f"[easyquotation] fetch error for {symbol}: {e}")
            return {}

    async def fetch_daily_kline(self, ts_code: str, trade_date: str) -> List[Dict[str, Any]]:
        """
        注意：easyquotation 仅支持实时快照。
        如果 trade_date 是今天，它返回的是最新价格。
        """
        symbol = self._convert_symbol(ts_code)
        
        # 异步调用
        data = await asyncio.to_thread(self._fetch_sync, symbol)
        
        if not data:
            return []
            
        return self.normalize_data(data, ts_code, trade_date)

    def normalize_data(self, data: Dict[str, Any], ts_code: str, trade_date: str) -> List[Dict[str, Any]]:
        # EasyQuotation 新浪源字段映射：
        # now: 当前价, close: 昨收, turnover: 成交量(股), volume: 成交额(元)
        
        results = []
        close_price = float(data.get('now', 0))
        pre_close = float(data.get('close', 0))
        
        # 处理成交量 (新浪源 'turnover' 是股)
        volume_shares = float(data.get('turnover', 0))
             
        # 处理成交额 (新浪源 'volume' 是元)
        amount_yuan = float(data.get('volume', 0))

        pct_chg = round((close_price - pre_close) / pre_close, 6) if pre_close > 0 else 0.0
        
        results.append({
            "ts_code": ts_code,
            "trade_date": trade_date,
            "open": float(data.get('open', 0)),
            "high": float(data.get('high', 0)),
            "low": float(data.get('low', 0)),
            "close": close_price,
            "pre_close": pre_close,
            "pct_chg": pct_chg,
            "volume": round(volume_shares / 100.0, 2), # 股转为手
            "amount": amount_yuan
        })
        return results
