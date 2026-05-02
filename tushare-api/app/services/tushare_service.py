import tushare as ts
import asyncio
import pandas as pd
from typing import Dict, Any, List, Optional
from app.utils.logger import get_logger
from app.core.config import settings

logger = get_logger("tushare-api.service")

class TushareService:
    def __init__(self):
        self.pro = ts.pro_api(settings.TUSHARE_TOKEN)
        
    def _df_to_records(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """将 DataFrame 转换为 Dict 列表并清洗无效的 float 值 (NaN/Inf)"""
        import math
        if df is None or df.empty:
            return []
            
        records = df.to_dict(orient='records')
        for r in records:
            for k, v in r.items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    r[k] = None
        return records

    async def _execute(self, api_name: str, **kwargs) -> pd.DataFrame:
        """执行 Tushare 接口调用，包含简单的重试机制"""
        kwargs = {k: v for k, v in kwargs.items() if v is not None and v != ""}
        
        for attempt in range(3):
            try:
                # Tushare 的 pro_api 是同步调用，使用 to_thread 异步化
                df = await asyncio.to_thread(self.pro.query, api_name, **kwargs)
                return df
            except Exception as e:
                err_msg = str(e)
                # 处理限流错误
                if "每分钟内最多查询" in err_msg or "频次限制" in err_msg or "请求过于频繁" in err_msg:
                    wait_time = (attempt + 1) * 3
                    logger.warning(f"Tushare 限流 [{api_name}], 等待 {wait_time}s 后重试 ({attempt+1}/3)...")
                    await asyncio.sleep(wait_time)
                    continue
                
                # 处理基础权限错误
                if "权限" in err_msg or "积分" in err_msg:
                    logger.error(f"Tushare 权限不足 [{api_name}]: {err_msg}")
                    raise Exception(f"Tushare 权限错误: {err_msg}")
                
                logger.error(f"Tushare 调用异常 [{api_name}]: {err_msg}")
                raise e
        
        raise Exception(f"Tushare 调用在 {api_name} 多次尝试后失败")

    async def get_stock_basic(self, list_status: str = 'L') -> List[Dict[str, Any]]:
        """获取股票基础信息 (120积分)"""
        df = await self._execute('stock_basic', list_status=list_status, fields='ts_code,symbol,name,area,industry,list_date')
        return self._df_to_records(df)

    async def get_daily(self, ts_code: str = None, trade_date: str = None, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """获取日线行情 (120积分, 非复权)"""
        df = await self._execute('daily', ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return self._df_to_records(df)

    async def get_trade_cal(self, exchange: str = '', start_date: str = '', end_date: str = '', is_open: int = None) -> List[Dict[str, Any]]:
        """获取交易日历 (120积分)"""
        df = await self._execute('trade_cal', exchange=exchange, start_date=start_date, end_date=end_date, is_open=is_open)
        return self._df_to_records(df)

    async def get_adj_factor(self, ts_code: str = '', trade_date: str = '', start_date: str = '', end_date: str = '') -> List[Dict[str, Any]]:
        """获取复权因子 (120积分)"""
        df = await self._execute('adj_factor', ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return self._df_to_records(df)

    async def get_index_basic(self, market: str = '') -> List[Dict[str, Any]]:
        """获取指数基础信息 (200积分)"""
        df = await self._execute('index_basic', market=market)
        return self._df_to_records(df)

    async def get_index_daily(self, ts_code: str = '', trade_date: str = '', start_date: str = '', end_date: str = '') -> List[Dict[str, Any]]:
        """获取指数日线行情 (200积分)"""
        df = await self._execute('index_daily', ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return self._df_to_records(df)

    async def get_suspend_d(self, ts_code: str = '', trade_date: str = '', start_date: str = '', end_date: str = '') -> List[Dict[str, Any]]:
        """获取每日停复牌信息 (120积分)"""
        df = await self._execute('suspend_d', ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return self._df_to_records(df)

    # -------------------------------------------------------------------------
    # 2000 积分以上接口
    # -------------------------------------------------------------------------

    async def get_forecast(self, ts_code: str = '', ann_date: str = '', start_date: str = '', end_date: str = '', period: str = '') -> List[Dict[str, Any]]:
        """获取业绩预告 (2000积分)"""
        df = await self._execute('forecast', ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period)
        return self._df_to_records(df)

    async def get_express(self, ts_code: str = '', ann_date: str = '', start_date: str = '', end_date: str = '', period: str = '') -> List[Dict[str, Any]]:
        """获取业绩快报 (2000积分)"""
        df = await self._execute('express', ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period)
        return self._df_to_records(df)

    async def get_dividend(self, ts_code: str = '', ann_date: str = '', imp_ann_date: str = '') -> List[Dict[str, Any]]:
        """获取分红送股 (2000积分)"""
        df = await self._execute('dividend', ts_code=ts_code, ann_date=ann_date, imp_ann_date=imp_ann_date)
        return self._df_to_records(df)

    async def get_stk_holdernumber(self, ts_code: str = '', ann_date: str = '', start_date: str = '', end_date: str = '') -> List[Dict[str, Any]]:
        """获取股东户数 (120积分)"""
        df = await self._execute('stk_holdernumber', ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date)
        return self._df_to_records(df)

    async def get_top10_holders(self, ts_code: str = '', ann_date: str = '', start_date: str = '', end_date: str = '', period: str = '') -> List[Dict[str, Any]]:
        """获取前十大股东 (120积分)"""
        df = await self._execute('top10_holders', ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period)
        return self._df_to_records(df)

    async def get_stk_rating(self, ts_code: str = '', ann_date: str = '', start_date: str = '', end_date: str = '') -> List[Dict[str, Any]]:
        """获取机构评级 (600积分)"""
        df = await self._execute('stk_rating', ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date)
        return self._df_to_records(df)
