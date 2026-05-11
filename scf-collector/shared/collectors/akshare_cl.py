import asyncio
import logging
import pandas as pd
from typing import List, Dict, Any
from .base import BaseCollector

logger = logging.getLogger(__name__)

class AkShareCollector(BaseCollector):
    @property
    def source_name(self) -> str:
        return "akshare"

    def _convert_symbol(self, ts_code: str) -> str:
        """将 '000001.SZ' 转换为 '000001'"""
        return ts_code.split('.')[0]

    def _convert_date(self, trade_date: str) -> str:
        """将 '2026-05-08' 转换为 '20260508'"""
        return trade_date.replace('-', '')

    def _fetch_sync(self, symbol: str, date_str: str) -> pd.DataFrame:
        """同步方法：调用 AkShare 获取 K 线"""
        # 在函数内部导入，避免全局加载导致 SCF 冷启动变慢
        import akshare as ak
        
        try:
            # adjust="" 代表不复权，实际可根据配置选择 "qfq" 或 "hfq"
            df = ak.stock_zh_a_hist(
                symbol=symbol, 
                period="daily", 
                start_date=date_str, 
                end_date=date_str, 
                adjust=""
            )
            return df
        except Exception as e:
            logger.error(f"[akshare] fetch error for {symbol} on {date_str}: {e}")
            return pd.DataFrame()

    async def fetch_daily_kline(self, ts_code: str, trade_date: str) -> List[Dict[str, Any]]:
        symbol = self._convert_symbol(ts_code)
        date_str = self._convert_date(trade_date)
        
        # 使用 asyncio.to_thread 将同步调用放入线程池
        df = await asyncio.to_thread(self._fetch_sync, symbol, date_str)
        
        if df is None or df.empty:
            return []
            
        return self.normalize_data(df, ts_code, trade_date)

    def normalize_data(self, df: pd.DataFrame, ts_code: str, trade_date: str) -> List[Dict[str, Any]]:
        results = []
        for _, row in df.iterrows():
            # AkShare 返回字段参考: 
            # 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
            
            open_price = float(row.get('开盘', 0))
            close_price = float(row.get('收盘', 0))
            change = float(row.get('涨跌额', 0))
            pre_close = close_price - change
            
            # AkShare 涨跌幅通常是百分比数值 (如 5.0 代表 5%)，需转化为小数 0.05
            pct_chg_raw = float(row.get('涨跌幅', 0))
            pct_chg = round(pct_chg_raw / 100.0, 6)

            results.append({
                "ts_code": ts_code,
                "trade_date": trade_date,
                "open": open_price,
                "high": float(row.get('最高', 0)),
                "low": float(row.get('最低', 0)),
                "close": close_price,
                "pre_close": round(pre_close, 4),
                "change": round(change, 4),
                "pct_chg": pct_chg,
                "vol": float(row.get('成交量', 0)), # AkShare 通常是手
                "amount": float(row.get('成交额', 0)) # AkShare 通常是元
            })
        return results
