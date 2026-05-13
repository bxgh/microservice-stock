import os
import asyncio
import logging
import pandas as pd
from typing import List, Dict, Any
from shared.utils.models import KLineModel
from .base import BaseCollector

logger = logging.getLogger(__name__)

class TushareCollector(BaseCollector):
    def __init__(self):
        import tushare as ts
        token = os.getenv("TUSHARE_TOKEN")
        if not token:
            logger.error("[tushare] TUSHARE_TOKEN environment variable is not set.")
            self.pro = None
        else:
            self.pro = ts.pro_api(token)

    @property
    def source_name(self) -> str:
        return "tushare"

    def _convert_date(self, trade_date: str) -> str:
        """将 '2026-05-08' 转换为 '20260508'"""
        return trade_date.replace('-', '')

    def _fetch_sync(self, ts_code: str, date_str: str) -> pd.DataFrame:
        """同步方法：调用 Tushare 获取 K 线"""
        if not self.pro:
            logger.error("[tushare] pro_api is not initialized.")
            return pd.DataFrame()
            
        try:
            df = self.pro.daily(ts_code=ts_code, start_date=date_str, end_date=date_str)
            return df
        except Exception as e:
            logger.error(f"[tushare] fetch error for {ts_code} on {date_str}: {e}")
            raise

    async def fetch_daily_kline(self, ts_code: str, trade_date: str) -> List[KLineModel]:
        date_str = self._convert_date(trade_date)
        
        # 使用 asyncio.to_thread 将同步调用放入线程池
        df = await asyncio.to_thread(self._fetch_sync, ts_code, date_str)
        
        if df is None or df.empty:
            return []
            
        return self.normalize_data(df, ts_code, trade_date)

    def _fetch_batch_daily_sync(self, date_str: str) -> pd.DataFrame:
        if not self.pro:
            logger.error("[tushare] pro_api is not initialized.")
            return pd.DataFrame()
        try:
            return self.pro.daily(trade_date=date_str)
        except Exception as e:
            logger.error(f"[tushare] fetch batch daily error for {date_str}: {e}")
            raise

    async def fetch_batch_daily_kline(self, trade_date: str) -> List[KLineModel]:
        """批量获取单日全 A 股票 K 线"""
        date_str = self._convert_date(trade_date)
        df = await asyncio.to_thread(self._fetch_batch_daily_sync, date_str)
        if df is None or df.empty:
            return []
        
        # 批量归一化逻辑
        results = []
        for _, row in df.iterrows():
            pct_chg_raw = float(row.get('pct_chg', 0)) if row.get('pct_chg') is not None else 0
            amount_raw = float(row.get('amount', 0)) if row.get('amount') is not None else 0
            results.append(KLineModel(
                ts_code=row.get('ts_code'),
                trade_date=trade_date,
                open=float(row.get('open', 0)),
                high=float(row.get('high', 0)),
                low=float(row.get('low', 0)),
                close=float(row.get('close', 0)),
                pre_close=float(row.get('pre_close', 0)),
                change=float(row.get('change', 0)),
                pct_chg=round(pct_chg_raw / 100.0, 6),
                volume=float(row.get('vol', 0)),
                amount=round(amount_raw * 1000.0, 2)
            ))
        return results

    def _fetch_adj_factor_sync(self, date_str: str) -> pd.DataFrame:
        if not self.pro:
            logger.error("[tushare] pro_api is not initialized.")
            return pd.DataFrame()
        try:
            return self.pro.adj_factor(trade_date=date_str)
        except Exception as e:
            logger.error(f"[tushare] fetch adj factor error for {date_str}: {e}")
            raise

    async def fetch_adj_factor(self, trade_date: str) -> List[Dict[str, Any]]:
        """获取复权因子"""
        date_str = self._convert_date(trade_date)
        df = await asyncio.to_thread(self._fetch_adj_factor_sync, date_str)
        return df.to_dict('records') if not df.empty else []

    def _fetch_sw_industry_members_sync(self) -> pd.DataFrame:
        if not self.pro:
            logger.error("[tushare] pro_api is not initialized.")
            return pd.DataFrame()
        try:
            # 获取申万行业成员 (全量拉链数据)
            return self.pro.index_member_all()
        except Exception as e:
            logger.error(f"[tushare] fetch sw industry members error: {e}")
            raise

    async def fetch_sw_industry_members(self) -> List[Dict[str, Any]]:
        """获取申万行业成员 (处理字段映射)"""
        df = await asyncio.to_thread(self._fetch_sw_industry_members_sync)
        if df is None or df.empty:
            return []
        
        # 归一化字段: l1_code -> index_code, ts_code -> con_code
        results = []
        for _, row in df.iterrows():
            results.append({
                "index_code": row.get('l1_code'),
                "index_name": row.get('l1_name'),
                "con_code": row.get('ts_code'),
                "con_name": row.get('name'),
                "in_date": row.get('in_date'),
                "out_date": row.get('out_date'),
                "is_new": row.get('is_new')
            })
        return results

    def _fetch_index_daily_sync(self, ts_code: str, date_str: str) -> pd.DataFrame:
        if not self.pro:
            logger.error("[tushare] pro_api is not initialized.")
            return pd.DataFrame()
        try:
            return self.pro.index_daily(ts_code=ts_code, trade_date=date_str)
        except Exception as e:
            logger.error(f"[tushare] fetch index daily error for {ts_code} on {date_str}: {e}")
            raise

    async def fetch_index_daily(self, ts_code: str, trade_date: str) -> List[KLineModel]:
        """获取指数行情"""
        date_str = self._convert_date(trade_date)
        df = await asyncio.to_thread(self._fetch_index_daily_sync, ts_code, date_str)
        if df is None or df.empty:
            return []
        
        # 归一化指数数据
        results = []
        for _, row in df.iterrows():
            pct_chg_raw = float(row.get('pct_chg', 0)) if row.get('pct_chg') is not None else 0
            amount_raw = float(row.get('amount', 0)) if row.get('amount') is not None else 0
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
                "volume": float(row.get('vol', 0)),
                "amount": round(amount_raw * 1000.0, 2)
            })
        return results

    def _fetch_calendar_sync(self, start_date: str, end_date: str) -> pd.DataFrame:
        if not self.pro:
            logger.error("[tushare] pro_api is not initialized.")
            return pd.DataFrame()
        try:
            return self.pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)
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
        if not self.pro:
            logger.error("[tushare] pro_api is not initialized.")
            return pd.DataFrame()
        try:
            # 获取上市状态为 L 的所有股票
            return self.pro.stock_basic(list_status='L', fields='ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type')
        except Exception as e:
            logger.error(f"[tushare] fetch stock list error: {e}")
            raise

    async def fetch_stock_list(self) -> List[Dict[str, Any]]:
        """获取全量股票列表"""
        df = await asyncio.to_thread(self._fetch_stock_list_sync)
        return df.to_dict('records') if not df.empty else []

    def _fetch_suspend_d_sync(self, date_str: str) -> pd.DataFrame:
        """[Backend Engineer] 修复：复用已初始化的 self.pro"""
        try:
            return self.pro.suspend_d(trade_date=date_str)
        except Exception as e:
            logger.error(f"[tushare] fetch suspend_d error for {date_str}: {e}")
            raise

    async def fetch_suspensions(self, trade_date: str) -> List[Dict[str, Any]]:
        """获取当日停牌列表（非交易日返回空列表属正常情况）"""
        date_str = self._convert_date(trade_date)
        df = await asyncio.to_thread(self._fetch_suspend_d_sync, date_str)
        if df.empty:
            logger.info(f"[tushare] suspend_d returned empty for {date_str} (non-trading day or no suspension).")
            return []
        return df.to_dict('records')

    def normalize_data(self, df: pd.DataFrame, ts_code: str, trade_date: str) -> List[KLineModel]:
        results = []
        for _, row in df.iterrows():
            pct_chg_raw = float(row.get('pct_chg', 0))
            amount_raw = float(row.get('amount', 0))

            results.append(KLineModel(
                ts_code=ts_code,
                trade_date=trade_date,
                open=float(row.get('open', 0)),
                high=float(row.get('high', 0)),
                low=float(row.get('low', 0)),
                close=float(row.get('close', 0)),
                pre_close=float(row.get('pre_close', 0)),
                change=float(row.get('change', 0)),
                pct_chg=round(pct_chg_raw / 100.0, 6),
                volume=float(row.get('vol', 0)), # Tushare 默认手
                amount=round(amount_raw * 1000.0, 2)
            ))
        return results
