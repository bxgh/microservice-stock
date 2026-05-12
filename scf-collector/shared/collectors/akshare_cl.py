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

    def _convert_symbol_sina(self, ts_code: str) -> str:
        """将 '600519.SH' 转换为 'sh600519'"""
        code, market = ts_code.split('.')
        return f"{market.lower()}{code}"

    def _fetch_sync(self, symbol: str, date_str: str) -> pd.DataFrame:
        """同步方法：调用 AkShare 获取 K 线 (东方财富源)"""
        import akshare as ak
        try:
            # 默认源：东方财富
            df = ak.stock_zh_a_hist(
                symbol=symbol, 
                period="daily", 
                start_date=date_str, 
                end_date=date_str, 
                adjust=""
            )
            return df
        except Exception as e:
            logger.warning(f"[akshare] EM source failed for {symbol}: {e}")
            return pd.DataFrame()

    def _fetch_sina_sync(self, sina_symbol: str, date_str: str) -> pd.DataFrame:
        """备选源：新浪财经"""
        import akshare as ak
        try:
            # 新浪源使用 sh/sz 前缀
            df = ak.stock_zh_a_daily(
                symbol=sina_symbol, 
                start_date=date_str, 
                end_date=date_str
            )
            return df
        except Exception as e:
            logger.error(f"[akshare] Sina source also failed for {sina_symbol}: {e}")
            return pd.DataFrame()

    async def fetch_daily_kline(self, ts_code: str, trade_date: str) -> List[Dict[str, Any]]:
        symbol = self._convert_symbol(ts_code)
        date_str = self._convert_date(trade_date)
        
        # 1. 尝试主数据源 (东方财富)
        df = await asyncio.to_thread(self._fetch_sync, symbol, date_str)
        
        # 2. 如果主源失败，尝试备选源 (新浪)
        if df is None or df.empty:
            logger.info(f"[akshare] Switching to Sina fallback for {ts_code}")
            sina_symbol = self._convert_symbol_sina(ts_code)
            df = await asyncio.to_thread(self._fetch_sina_sync, sina_symbol, date_str)
            if df is not None and not df.empty:
                return self.normalize_sina_data(df, ts_code, trade_date)
            return []
            
        return self.normalize_data(df, ts_code, trade_date)

    def normalize_sina_data(self, df: pd.DataFrame, ts_code: str, trade_date: str) -> List[Dict[str, Any]]:
        """归一化新浪源数据"""
        results = []
        for _, row in df.iterrows():
            # 新浪返回字段: date, open, high, low, close, volume, outstanding_share, turnover
            close_price = float(row.get('close', 0))
            # 新浪源不提供 pre_close 和 amount，需要特殊处理或后续补偿
            # 这里暂时设为 0，审计逻辑会识别到 PARTIAL
            results.append({
                "ts_code": ts_code,
                "trade_date": trade_date,
                "open": float(row.get('open', 0)),
                "high": float(row.get('high', 0)),
                "low": float(row.get('low', 0)),
                "close": close_price,
                "pre_close": 0.0, 
                "pct_chg": 0.0,
                "volume": float(row.get('volume', 0)) / 100.0, # 新浪通常是股，转为手
                "amount": 0.0 
            })
        return results

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
                "volume": float(row.get('成交量', 0)), # AkShare 通常是手
                "amount": float(row.get('成交额', 0)) # AkShare 通常是元
            })
        return results
