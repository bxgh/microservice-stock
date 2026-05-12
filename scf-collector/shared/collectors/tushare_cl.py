import os
import asyncio
import logging
import pandas as pd
from typing import List, Dict, Any
from .base import BaseCollector

logger = logging.getLogger(__name__)

class TushareCollector(BaseCollector):
    @property
    def source_name(self) -> str:
        return "tushare"

    def _convert_date(self, trade_date: str) -> str:
        """将 '2026-05-08' 转换为 '20260508'"""
        return trade_date.replace('-', '')

    def _fetch_sync(self, ts_code: str, date_str: str) -> pd.DataFrame:
        """同步方法：调用 Tushare 获取 K 线"""
        # 在函数内部导入，避免全局加载导致 SCF 冷启动变慢
        import tushare as ts
        
        token = os.getenv("TUSHARE_TOKEN")
        if not token:
            logger.error("[tushare] TUSHARE_TOKEN environment variable is not set.")
            return pd.DataFrame()
            
        try:
            pro = ts.pro_api(token)
            df = pro.daily(ts_code=ts_code, start_date=date_str, end_date=date_str)
            return df
        except Exception as e:
            logger.error(f"[tushare] fetch error for {ts_code} on {date_str}: {e}")
            raise

    async def fetch_daily_kline(self, ts_code: str, trade_date: str) -> List[Dict[str, Any]]:
        date_str = self._convert_date(trade_date)
        
        # 使用 asyncio.to_thread 将同步调用放入线程池
        df = await asyncio.to_thread(self._fetch_sync, ts_code, date_str)
        
        if df is None or df.empty:
            return []
            
        return self.normalize_data(df, ts_code, trade_date)

    def _fetch_calendar_sync(self, start_date: str, end_date: str) -> pd.DataFrame:
        import tushare as ts
        token = os.getenv("TUSHARE_TOKEN")
        try:
            pro = ts.pro_api(token)
            return pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)
        except Exception as e:
            logger.error(f"[tushare] fetch calendar error: {e}")
            raise

    async def fetch_trading_calendar(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取交易日历"""
        s_date = self._convert_date(start_date)
        e_date = self._convert_date(end_date)
        df = await asyncio.to_thread(self._fetch_calendar_sync, s_date, e_date)
        return df.to_dict('records') if not df.empty else []

    def _fetch_stock_list_sync(self) -> pd.DataFrame:
        import tushare as ts
        token = os.getenv("TUSHARE_TOKEN")
        try:
            pro = ts.pro_api(token)
            # 获取上市状态为 L 的所有股票
            return pro.stock_basic(list_status='L', fields='ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type')
        except Exception as e:
            logger.error(f"[tushare] fetch stock list error: {e}")
            raise

    async def fetch_stock_list(self) -> List[Dict[str, Any]]:
        """获取全量股票列表"""
        df = await asyncio.to_thread(self._fetch_stock_list_sync)
        return df.to_dict('records') if not df.empty else []

    def normalize_data(self, df: pd.DataFrame, ts_code: str, trade_date: str) -> List[Dict[str, Any]]:
        results = []
        for _, row in df.iterrows():
            # Tushare 返回字段参考: 
            # ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
            
            # Tushare 陷阱修复：
            # 1. pct_chg 是百分比（如 5.0），需除以 100 转为小数
            # 2. amount 是千元，需乘以 1000 转为元
            
            pct_chg_raw = float(row.get('pct_chg', 0))
            amount_raw = float(row.get('amount', 0))

            results.append({
                "ts_code": ts_code,
                "trade_date": trade_date,
                "open": float(row.get('open', 0)),
                "high": float(row.get('high', 0)),
                "low": float(row.get('low', 0)),
                "close": float(row.get('close', 0)),
                "pre_close": float(row.get('pre_close', 0)),
                "change": float(row.get('change', 0)),
                "pct_chg": round(pct_chg_raw / 100.0, 6),
                "volume": float(row.get('vol', 0)), # Tushare 默认手
                "amount": round(amount_raw * 1000.0, 2)
            })
        return results
