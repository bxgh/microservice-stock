import asyncio
import logging
import pandas as pd
from typing import List, Dict, Any
from .base import BaseCollector

logger = logging.getLogger(__name__)

class MootdxCollector(BaseCollector):
    @property
    def source_name(self) -> str:
        return "mootdx"

    def _convert_symbol(self, ts_code: str) -> str:
        """将 '000001.SZ' 转换为 '000001'"""
        return ts_code.split('.')[0]

    def _fetch_sync(self, symbol: str, trade_date: str) -> pd.DataFrame:
        """同步方法：调用 mootdx 获取 K 线"""
        # 在函数内部导入，避免全局加载导致 SCF 冷启动变慢
        from mootdx.quotes import Quotes
        
        try:
            # 初始化客户端 (最好加上重试或使用连接池，此处简化每次实例化)
            client = Quotes.factory(market='std')
            
            # category=9 代表日 K 线，获取最近 10 条足够覆盖当日（预防节假日）
            df = client.bars(symbol=symbol, category=9, offset=10)
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 过滤指定日期的数据
            # trade_date 可能是 '2026-05-08'，mootdx 返回的 datetime 可能是包含时间的
            df['date_str'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
            df_filtered = df[df['date_str'] == trade_date]
            
            return df_filtered
        except Exception as e:
            logger.error(f"[mootdx] fetch error for {symbol} on {trade_date}: {e}")
            return pd.DataFrame()

    async def fetch_daily_kline(self, ts_code: str, trade_date: str) -> List[Dict[str, Any]]:
        symbol = self._convert_symbol(ts_code)
        
        # 使用 asyncio.to_thread 将同步调用放入线程池
        df = await asyncio.to_thread(self._fetch_sync, symbol, trade_date)
        
        if df.empty:
            return []
            
        return self.normalize_data(df, ts_code, trade_date)

    def normalize_data(self, df: pd.DataFrame, ts_code: str, trade_date: str) -> List[Dict[str, Any]]:
        results = []
        for _, row in df.iterrows():
            # 根据 mootdx 的常规返回结构进行转换
            # mootdx 字段: open, close, high, low, vol, amount, pre_close
            # 注意 mootdx 返回的 vol 是手，amount 是元
            
            open_price = float(row.get('open', 0))
            close_price = float(row.get('close', 0))
            pre_close = float(row.get('pre_close', open_price)) # 如果没有 pre_close，估算一个
            change = close_price - pre_close
            pct_chg = round(change / pre_close, 6) if pre_close > 0 else 0.0

            results.append({
                "ts_code": ts_code,
                "trade_date": trade_date,
                "open": open_price,
                "high": float(row.get('high', 0)),
                "low": float(row.get('low', 0)),
                "close": close_price,
                "pre_close": pre_close,
                "change": round(change, 4),
                "pct_chg": pct_chg, # 小数形式
                "vol": float(row.get('vol', 0)),
                "amount": float(row.get('amount', 0))
            })
        return results
