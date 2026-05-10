"""
Mootdx Handler
通达信直连数据源处理器

职责:
- 管理 mootdx 客户端连接池的生命周期
- 提供实时行情、分笔、K线数据获取接口
- 异步包装同步调用
- 通过连接池实现负载均衡
"""
import asyncio
import logging
import os
from typing import List, Dict, Any
import pandas as pd
from mootdx.quotes import Quotes
from contextlib import asynccontextmanager

from utils.field_mapper import standardize_mootdx_fields
from core.tdx_pool import TDXClientPool

# 内联默认值（避免外部依赖）
DEFAULT_FREQUENCY = "d"

logger = logging.getLogger("mootdx-handler")


class MootdxHandler:
    """
    通达信（mootdx）数据源处理器
    
    封装 mootdx 库的调用逻辑，提供异步接口。
    使用连接池实现负载均衡，突破单节点并发限制。
    """
    
    def __init__(self, pool_size: int = None):
        """
        初始化 Handler
        
        Args:
            pool_size: 连接池大小，默认从环境变量 TDX_POOL_SIZE 读取，否则为 3
        """
        if pool_size is None:
            pool_size = int(os.getenv("TDX_POOL_SIZE", "3"))
        self.pool = TDXClientPool(size=pool_size)
        self._lock = asyncio.Lock()
    
    
    @asynccontextmanager
    async def acquire_client(self):
        """
        获取一个独占的客户端连接 (Async Context Manager)
        用法:
            async with handler.acquire_client() as client:
                client.quotes(...)
        """
        client = await self.pool.acquire()
        try:
            yield client
        finally:
            await self.pool.release(client)

    
    async def initialize(self) -> None:
        """
        初始化 TDX 连接池
        
        创建多个 TDX 客户端连接，每个连接自动选择最佳服务器
        """
        async with self._lock:
            await self.pool.initialize()
            logger.info(f"✓ MootdxHandler 就绪 (pool_size={self.pool.size})")
    
    async def close(self) -> None:
        """
        关闭连接池
        """
        async with self._lock:
            await self.pool.close()
            logger.info("MootdxHandler 已关闭")
    
    def get_pool_status(self) -> dict:
        """获取连接池状态"""
        return self.pool.get_status()
    async def get_quotes(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        获取实时行情
        
        Args:
            codes: 股票代码列表
            params: 额外参数（暂未使用）
        
        Returns:
            DataFrame 包含字段:
            - code: 股票代码
            - name: 股票名称
            - open, high, low, price: OHLC
            - bid1-5, ask1-5: 五档买卖
            - volume, amount: 成交量/额
        """
        if not codes:
            return pd.DataFrame()
            
        async with self.acquire_client() as client:
            if not client:
                logger.warning("Mootdx client not initialized")
                return pd.DataFrame()

            loop = asyncio.get_event_loop()
            try:
                data = await loop.run_in_executor(
                    None,
                    lambda: client.quotes(symbol=list(codes))
                )
                if data is not None:
                    # 应用标准化字段映射
                    data = standardize_mootdx_fields(data, data_type='quotes')
                    # 修复 NaN 导致 JSON 序列化失败的问题
                    data = data.astype(object)
                    data = data.where(pd.notnull(data), None)

                return data if data is not None else pd.DataFrame()
            except Exception as e:
                logger.error(f"Mootdx get_quotes failed: {e}")
                return pd.DataFrame()
    
    async def get_tick(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        获取分笔成交数据
        
        Args:
            codes: 股票代码列表（仅支持单个代码）
            params: 额外参数（暂未使用）
        
        Returns:
            DataFrame 包含字段:
            - time: 时间
            - price: 成交价
            - volume: 成交量
            - type: 买卖类型
        
        Raises:
            ValueError: 未指定股票代码
        """
        if not codes:
            raise ValueError("No code specified for TICK")
            
        async with self.acquire_client() as client:
            if not client:
                logger.warning("Mootdx client not initialized")
                return pd.DataFrame()
        
            # 提取参数
            date = params.get("date")
            start = int(params.get("start", 0))
            offset = int(params.get("offset", 800))
            
            loop = asyncio.get_event_loop()
            try:
                if date is not None:
                    # 历史成交 (Plural: transactions)
                    data = await loop.run_in_executor(
                        None,
                        lambda: client.transactions(
                            symbol=codes[0],
                            date=date,
                            start=start,
                            offset=offset
                        )
                    )
                else:
                    # 当日实时成交 (Singular: transaction)
                    # Use raw symbol with prefix to ensure mootdx identifies market correctly
                    symbol = codes[0]
                    
                    data = await loop.run_in_executor(
                        None,
                        lambda: client.transaction(
                            symbol=symbol,
                            start=start,
                            offset=offset
                        )
                    )
                    
                # 集成标准化逻辑
                if data is not None:
                    data = standardize_mootdx_fields(data, data_type='tick')
                    # 修复 NaN 导致 JSON 序列化失败的问题
                    # 关键：必须先转换为 object 类型，否则 float 列中的 None 会被自动转回 NaN
                    data = data.astype(object)
                    data = data.where(pd.notnull(data), None)
                return data if data is not None else pd.DataFrame()
            except Exception as e:
                logger.error(f"Mootdx get_tick failed: {e}")
                return pd.DataFrame()
    
    async def get_history(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        获取历史K线数据
        
        Args:
            codes: 股票代码列表（仅支持单个代码）
            params: 参数
                - frequency: 频率 (d/w/m)
                - start: 起始位置（默认0）
                - offset: 数据条数（默认500，最大800）
        
        Returns:
            DataFrame 包含字段:
            - date: 日期
            - open, high, low, close: OHLC
            - volume, amount: 成交量/额
        
        Note:
            - mootdx 不支持复权数据
            - 最多返回800条历史数据
        
        Raises:
            ValueError: 未指定股票代码
        """
        if not codes:
            raise ValueError("No code specified for HISTORY")
            
        async with self.acquire_client() as client:
            if not client:
                logger.warning("Mootdx client not initialized")
                return pd.DataFrame()
        
            # 频率映射: d/w/m -> mootdx frequency code
            frequency = params.get("frequency", DEFAULT_FREQUENCY)
            freq_map = {"d": 9, "w": 6, "m": 5}
            mootdx_freq = freq_map.get(frequency, 9)
            
            # 数据范围
            start = params.get("start", 0)
            offset = min(params.get("offset", 500), 800)  # 最大800条
            
            loop = asyncio.get_event_loop()
            try:
                data = await loop.run_in_executor(
                    None,
                    lambda: client.bars(
                        symbol=codes[0],
                        frequency=mootdx_freq,
                        start=start,
                        offset=offset
                    )
                )
                return data if data is not None else pd.DataFrame()
            except Exception as e:
                logger.error(f"Mootdx get_history failed: {e}")
                return pd.DataFrame()
    
    async def get_stocks(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            codes: 股票代码列表（未使用，返回全市场）
            params: 参数
                - market: 0=深圳, 1=上海, None=全市场
        
        Returns:
            DataFrame 包含字段:
            - code: 股票代码
            - name: 股票名称（可能为空）
            - market: 市场代码
        
        Note:
            - 返回约 48,000+ 只股票
            - 包含股票、ETF、债券等
        """
        market = params.get("market")
        
        async with self.acquire_client() as client:
            if not client:
                logger.warning("Mootdx client not initialized")
                return pd.DataFrame()
        
            loop = asyncio.get_event_loop()
            try:
                if market is not None:
                    # 单个市场
                    data = await loop.run_in_executor(
                        None,
                        lambda: client.stocks(market=market)
                    )
                else:
                    # 全市场：合并上海+深圳
                    sh_data = await loop.run_in_executor(
                        None,
                        lambda: client.stocks(market=1)
                    )
                    sz_data = await loop.run_in_executor(
                        None,
                        lambda: client.stocks(market=0)
                    )
                    data = pd.concat([sh_data, sz_data], ignore_index=True)
                
                return data if data is not None else pd.DataFrame()
            except Exception as e:
                logger.error(f"Mootdx get_stocks failed: {e}")
                return pd.DataFrame()
    
    async def get_finance_info(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        获取股票基础财务信息
        
        Args:
            codes: 股票代码列表
            params: 额外参数（暂未使用）
        
        Returns:
            DataFrame 包含字段:
            - code: 股票代码
            - liutongguben: 流通股本
            - zongguben: 总股本
            - province: 省份
            - industry: 行业
            - ipo_date: 上市日期
            - updated_date: 更新日期
        
        Note:
            - 数据来自通达信内置数据
            - 更新频率可能不如专业财务数据源
        """
        if not codes:
            return pd.DataFrame()
            
        async with self.acquire_client() as client:
            if not client:
                logger.warning("Mootdx client not initialized")
                return pd.DataFrame()
        
            loop = asyncio.get_event_loop()
            results = []
            
            try:
                for code in codes:
                    data = await loop.run_in_executor(
                        None,
                        lambda c=code: client.finance(symbol=c)
                    )
                    if data is not None and not data.empty:
                        results.append(data)
                
                return pd.concat(results, ignore_index=True) if results else pd.DataFrame()
            except Exception as e:
                logger.error(f"Mootdx get_finance_info failed: {e}")
                return pd.DataFrame()
    
    async def get_xdxr(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        获取除权除息数据
        
        Args:
            codes: 股票代码列表（仅支持单个代码）
            params: 额外参数（暂未使用）
        
        Returns:
            DataFrame 包含字段:
            - year, month, day: 日期
            - category: 类别
            - fenhong: 分红（每股）
            - songzhuangu: 送转股比例
            - peigu: 配股比例
            - peigujia: 配股价格
            - suogu: 缩股比例
            - panqianliutong: 盘前流通股本
            - panhouliutong: 盘后流通股本
        
        Note:
            - 用于计算复权价格
            - 历史分红记录完整
        
        Raises:
            ValueError: 未指定股票代码
        """
        if not codes:
            raise ValueError("No code specified for XDXR")
            
        async with self.acquire_client() as client:
            if not client:
                logger.warning("Mootdx client not initialized")
                return pd.DataFrame()
        
            loop = asyncio.get_event_loop()
            try:
                data = await loop.run_in_executor(
                    None,
                    lambda: client.xdxr(symbol=codes[0])
                )
                return data if data is not None else pd.DataFrame()
            except Exception as e:
                logger.error(f"Mootdx get_xdxr failed: {e}")
                return pd.DataFrame()
    
    async def get_index_bars(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        获取指数历史K线数据
        
        Args:
            codes: 指数代码列表（仅支持单个代码）
                - 000001: 上证指数
                - 399001: 深证成指
                - 399006: 创业板指
            params: 参数
                - frequency: 频率 (d/w/m)
                - start: 起始位置（默认0）
                - offset: 数据条数（默认500，最大800）
        
        Returns:
            DataFrame 包含字段:
            - date: 日期
            - open, high, low, close: OHLC
            - volume, amount: 成交量/额
            - up_count: 上涨家数
            - down_count: 下跌家数
        
        Raises:
            ValueError: 未指定指数代码
        """
        if not codes:
            raise ValueError("No code specified for INDEX_BARS")
            
        async with self.acquire_client() as client:
            if not client:
                logger.warning("Mootdx client not initialized")
                return pd.DataFrame()
        
            # 频率映射: d/w/m -> mootdx frequency code
            frequency = params.get("frequency", DEFAULT_FREQUENCY)
            freq_map = {"d": 9, "w": 6, "m": 5}
            mootdx_freq = freq_map.get(frequency, 9)
            
            # 数据范围
            start = params.get("start", 0)
            offset = min(params.get("offset", 500), 800)  # 最大800条
            
            loop = asyncio.get_event_loop()
            try:
                data = await loop.run_in_executor(
                    None,
                    lambda: client.index_bars(
                        symbol=codes[0],
                        frequency=mootdx_freq,
                        start=start,
                        offset=offset
                    )
                )
                return data if data is not None else pd.DataFrame()
            except Exception as e:
                logger.error(f"Mootdx get_index_bars failed: {e}")
                return pd.DataFrame()

