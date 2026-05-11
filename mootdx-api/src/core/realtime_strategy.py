"""
Mootdx Realtime Delta Strategy
Designed for high-frequency, incremental tick data acquisition.
"""
import logging
import asyncio
import pandas as pd
import datetime
from typing import List, Dict, Optional, Tuple, Any
from mootdx.quotes import Quotes

logger = logging.getLogger("realtime-strategy")

class RealtimeDeltaStrategy:
    """
    实时增量采集策略
    
    核心逻辑：
    1. 仅抓取最新的成交明细（默认 start=0, offset=2000）。
    2. 目标是极速获取最新数据，填补 Snapshot Recorder 发现的 "成交量缺口"。
    3. 不做全日完整性校验，只关注最新一笔。
    """
    
    def __init__(self):
        # 默认只抓取最近 2000 笔
        # 在高频模式下，每次 Snapshot 间隔（3秒）产生的成交量通常 < 100 手
        # 但为了应对 "断线重连" 或 "突发爆量"，我们抓取 2000 笔是安全的缓冲
        self.default_offset = 2000

    async def execute_intraday(self, client: Quotes, symbol: str, date: str) -> Tuple[Optional[List[Dict]], bool]:
        """
        执行盘中增量采集
        
        Args:
            client: Mootdx Quotes 客户端
            symbol: 股票代码
            date: 日期 YYYYMMDD
            
        Returns:
            (List[Dict], bool): (数据列表, 是否包含09:25数据-此处永远为False因为不强求)
        """
        # 标准化 symbol
        clean_symbol = symbol
        for prefix in ['sh.', 'sz.', 'sh', 'sz']:
            if symbol.lower().startswith(prefix):
                clean_symbol = symbol[len(prefix):]
                break
        
        # logger.debug(f"Executing delta fetch for {clean_symbol}")
        
        loop = asyncio.get_event_loop()
        
        # Check if date is today
        now = datetime.datetime.now()
        today_dash = now.strftime("%Y-%m-%d")
        today_plain = now.strftime("%Y%m%d")
        is_today = (date == today_dash) or (date == today_plain)
        
        try:
            # 1. 也是唯一的一步：获取最新数据
            if is_today:
                # Use Realtime API (singular 'transaction') for Today
                batch_df = await loop.run_in_executor(
                    None,
                    lambda: client.transaction(
                        symbol=clean_symbol,
                        start=0,          # 0 表示从最新倒推
                        offset=self.default_offset
                    )
                )
            else:
                # Use History API (plural 'transactions') for Past Dates
                batch_df = await loop.run_in_executor(
                    None,
                    lambda: client.transactions(
                        symbol=clean_symbol,
                        date=date,
                        start=0,
                        offset=self.default_offset
                    )
                )
            
            if batch_df is None or batch_df.empty:
                return None, False
            
            # 2. 转换格式
            # Mootdx returns: time, price, vol, buyorsell, etc.
            # Convert to list of dicts for protocol compatibility
            records = batch_df.to_dict('records')
            
            # 3. 简单校验（可选）
            # 我们假设 upstream (consumer) 会做去重
            # 这里直接返回"脏"数据即可，追求速度
            
            return records, False # has_0925 is not guaranteed/checked here
            
        except Exception as e:
            logger.warning(f"Delta fetch failed for {symbol}: {e}")
            return None, False
