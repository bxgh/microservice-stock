import asyncio
import logging
import pandas as pd
from typing import List, Dict, Any
from shared.utils.models import KLineModel
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

    def _fetch_all_spot_sync(self) -> pd.DataFrame:
        """同步方法：调用 AkShare 获取全 A 股实时快照 (东方财富源)"""
        import akshare as ak
        try:
            # 接口：stock_zh_a_spot_em (全量快照)
            # 该接口返回全 A 股当日最新行情（非历史）
            df = ak.stock_zh_a_spot_em()
            return df
        except Exception as e:
            logger.error(f"[akshare] Batch spot fetch failed: {e}")
            return pd.DataFrame()

    async def fetch_all_stock_spot(self) -> pd.DataFrame:
        """异步封装：获取全 A 股实时快照"""
        return await asyncio.to_thread(self._fetch_all_spot_sync)

    async def fetch_daily_kline(self, ts_code: str, trade_date: str) -> List[KLineModel]:
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

    def normalize_sina_data(self, df: pd.DataFrame, ts_code: str, trade_date: str) -> List[KLineModel]:
        """归一化新浪源数据"""
        results = []
        for _, row in df.iterrows():
            close_price = float(row.get('close', 0))
            results.append(KLineModel(
                ts_code=ts_code,
                trade_date=trade_date,
                open=float(row.get('open', 0)),
                high=float(row.get('high', 0)),
                low=float(row.get('low', 0)),
                close=close_price,
                pre_close=0.0, 
                pct_chg=0.0,
                volume=float(row.get('volume', 0)) / 100.0, 
                amount=0.0 
            ))
        return results

    def normalize_data(self, df: pd.DataFrame, ts_code: str, trade_date: str) -> List[KLineModel]:
        results = []
        for _, row in df.iterrows():
            close_price = float(row.get('收盘', 0))
            change = float(row.get('涨跌额', 0))
            pre_close = close_price - change
            
            pct_chg_raw = float(row.get('涨跌幅', 0))
            pct_chg = round(pct_chg_raw / 100.0, 6)

            results.append(KLineModel(
                ts_code=ts_code,
                trade_date=trade_date,
                open=float(row.get('开盘', 0)),
                high=float(row.get('最高', 0)),
                low=float(row.get('最低', 0)),
                close=close_price,
                pre_close=round(pre_close, 4),
                change=round(change, 4),
                pct_chg=pct_chg,
                volume=float(row.get('成交量', 0)),
                amount=float(row.get('成交额', 0))
            ))
        return results

    def _fetch_limit_pool_sync(self, date_str: str, pool_type: str = 'zt') -> pd.DataFrame:
        import akshare as ak
        try:
            if pool_type == 'zt':
                return ak.stock_zt_pool_em(date=date_str)
            elif pool_type == 'dt':
                return ak.stock_zt_pool_dtgc_em(date=date_str)
            elif pool_type == 'zb':
                return ak.stock_zt_pool_zbgc_em(date=date_str)
            elif pool_type == 'lian':
                return ak.stock_zt_pool_previous_em(date=date_str)
            else:
                raise ValueError(f"Unsupported pool_type: {pool_type}")
        except Exception as e:
            logger.error(f"[akshare] fetch_limit_pool error for {date_str} ({pool_type}): {e}")
            return pd.DataFrame()

    async def fetch_limit_pool(self, trade_date: str, pool_type: str = 'zt') -> List[Dict[str, Any]]:
        """[E15-S1-T1] 异步获取 AkShare 涨跌停/炸板/连板池数据并对齐字段"""
        date_str = self._convert_date(trade_date)
        df = await asyncio.to_thread(self._fetch_limit_pool_sync, date_str, pool_type)
        if df is None or df.empty:
            return []

        result = []
        for _, row in df.iterrows():
            def clean_val(v, default=None):
                if v is None or pd.isna(v): 
                    return default
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return default

            # 对齐百分比与金额口径
            pct_chg_raw = clean_val(row.get("涨跌幅"))
            pct_chg = round(pct_chg_raw / 100.0, 6) if pct_chg_raw is not None else None

            turnover_rate_raw = clean_val(row.get("换手率"))
            turnover_rate = round(turnover_rate_raw / 100.0, 6) if turnover_rate_raw is not None else None

            item = {
                "ts_code": row.get("代码"),
                "name": row.get("名称"),
                "close": clean_val(row.get("最新价")),
                "pct_chg": pct_chg,
                "amount": clean_val(row.get("成交额")),
                "circ_mv": clean_val(row.get("流通市值")),
                "turnover_rate": turnover_rate,
                "first_limit_time": row.get("首次封板时间"),
                "last_limit_time": row.get("最后封板时间"),
                "board_height": clean_val(row.get("连板数")),
                "seal_money": clean_val(row.get("封板资金")),
                "seal_count": clean_val(row.get("封板次数")),
                "open_times": clean_val(row.get("炸板次数")),
                "industry": row.get("所属行业"),
            }
            result.append(item)
        return result
