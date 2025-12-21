import asyncio
from typing import Dict, Any, List, Optional
import baostock as bs
from app.utils.logger import get_logger

logger = get_logger("baostock-api.service")

class BaoStockService:
    """包装 BaoStock 数据服务
    
    使用全局锁 (asyncio.Lock) 保证 BaoStock 单连接的线程安全性。
    所有同步 I/O 操作通过 asyncio.to_thread 在线程池中执行。
    """
    
    def __init__(self):
        self.lock = asyncio.Lock()
        
    async def get_kline(
        self, 
        code: str, 
        frequency: str = "d", 
        adjust: str = "2", 
        start_date: str = "2020-01-01", 
        end_date: str = ""
    ) -> List[Dict[str, Any]]:
        """异步获取 K 线数据
        
        Args:
            code: 股票代码，如 "sh.600519" 或 "600519"
            frequency: 频率，d=日, w=周, m=月, 5=5分钟
            adjust: 复权类型，"1"=后复权, "2"=前复权, "3"=不复权
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            
        Returns:
            K线数据列表，最多返回 500 条记录
        """
        # 补全代码前缀
        if not code.startswith(("sh.", "sz.")):
            code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
            
        async with self.lock:
            try:
                # 使用 to_thread 执行阻塞调用
                rs = await asyncio.to_thread(
                    bs.query_history_k_data_plus,
                    code=code,
                    fields="date,open,high,low,close,volume,amount,turn,pctChg",
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency,
                    adjustflag=adjust
                )
                
                if rs.error_code != "0":
                    logger.error(f"BaoStock查询失败: {rs.error_msg}")
                    return []
                
                result = []
                # 注意: rs.next() 和 rs.get_row_data() 也是阻塞的，理想情况下也应在线程中处理
                # 但这里简单起见，如果数据量不大，可以接受，或者继续封装
                def fetch_all(rs_obj):
                    data = []
                    while rs_obj.next():
                        data.append(rs_obj.get_row_data())
                    return data
                
                rows = await asyncio.to_thread(fetch_all, rs)
                
                for row in rows:
                    result.append({
                        "date": row[0],
                        "open": float(row[1]) if row[1] else None,
                        "high": float(row[2]) if row[2] else None,
                        "low": float(row[3]) if row[3] else None,
                        "close": float(row[4]) if row[4] else None,
                        "volume": int(float(row[5])) if row[5] else None,
                        "amount": float(row[6]) if row[6] else None,
                        "turn": float(row[7]) if row[7] else None,
                        "pctChg": float(row[8]) if row[8] else None,
                    })
                
                # 限制返回数量
                return result[-500:] if len(result) > 500 else result
            except Exception as e:
                logger.error(f"BaoStock查询异常: {e}")
                return []

    async def get_index_cons(self, index_code: str) -> List[Dict[str, Any]]:
        """获取指数成分股
        
        Args:
            index_code: 指数代码，如 "sz.399300" (沪深300)
            
        Returns:
            成分股列表，包含 code 和 name 字段
        """
        async with self.lock:
            try:
                rs = await asyncio.to_thread(bs.query_all_stock, day="")
                if rs.error_code != "0":
                    return []
                
                # 实际中 baostock 提供的指数成分股接口可能不同，这里以现有设计为准
                # 或根据实际接口 query_sz50_stocks / query_hs300_stocks 等
                # 标准化识别指数类型
                if index_code in ["sh.000300", "sz.399300"] or "300" in index_code:
                    rs = await asyncio.to_thread(bs.query_hs300_stocks)
                elif index_code in ["sh.000016"] or "50" in index_code:
                    rs = await asyncio.to_thread(bs.query_sz50_stocks)
                elif index_code in ["sh.000905", "sz.399005"] or "500" in index_code:
                    rs = await asyncio.to_thread(bs.query_zz500_stocks)
                else:
                    logger.warning(f"不支持的指数代码: {index_code}")
                    return []
                
                def fetch_all(rs_obj):
                    data = []
                    while rs_obj.next():
                        data.append(rs_obj.get_row_data())
                    return data
                
                rows = await asyncio.to_thread(fetch_all, rs)
                
                result = []
                for row in rows:
                    # 接口返回通常是 code, code_name
                    result.append({
                        "code": row[1],
                        "name": row[2] if len(row) > 2 else "",
                    })
                return result
            except Exception as e:
                logger.error(f"BaoStock获取指数成分异常: {e}")
                return []

    async def get_industry_classify(self) -> List[Dict[str, Any]]:
        """获取行业分类"""
        async with self.lock:
            try:
                rs = await asyncio.to_thread(bs.query_stock_industry)
                
                if rs.error_code != "0":
                    logger.error(f"BaoStock查询行业分类失败: {rs.error_msg}")
                    return []
                
                def fetch_all(rs_obj):
                    data = []
                    while rs_obj.next():
                        data.append(rs_obj.get_row_data())
                    return data
                
                rows = await asyncio.to_thread(fetch_all, rs)
                
                # 统计每个行业的股票数
                industries = {}
                for row in rows:
                    code = row[1] if len(row) > 1 else ""
                    industry = row[3] if len(row) > 3 else ""
                    
                    if industry:
                        if industry not in industries:
                            industries[industry] = []
                        industries[industry].append(code)
                
                # 转换为列表格式
                result = []
                for industry, stocks in industries.items():
                    result.append({
                        "industry": industry,
                        "stock_count": len(stocks),
                    })
                
                return result
            except Exception as e:
                logger.error(f"BaoStock获取行业分类异常: {e}")
                return []

    async def get_valuation_history(
        self, 
        code: str, 
        start_date: str = "2020-01-01", 
        end_date: str = ""
    ) -> List[Dict[str, Any]]:
        """获取历史估值数据 (PE/PB)
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            历史估值列表，包含以下字段:
            - date: 交易日期 (YYYY-MM-DD)
            - price: 收盘价 (除权后)
            - pe: 滚动市盈率 (PE-TTM)
            - pb: 市净率 (PB-MRQ)
            - ps: 市销率 (PS-TTM)
        """
        if not code.startswith(("sh.", "sz.")):
            code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
            
        async with self.lock:
            try:
                rs = await asyncio.to_thread(
                    bs.query_history_k_data_plus,
                    code=code,
                    fields="date,close,peTTM,pbMRQ,psTTM",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="3"
                )
                
                if rs.error_code != "0":
                    logger.error(f"BaoStock查询估值失败: {rs.error_msg}")
                    return []
                
                def _fetch_all(rs_obj):
                    data = []
                    while rs_obj.next():
                        data.append(rs_obj.get_row_data())
                    return data
                
                rows = await asyncio.to_thread(_fetch_all, rs)
                
                result = []
                for row in rows:
                    result.append({
                        "date": row[0],
                        "price": float(row[1]) if row[1] else None,
                        "pe": float(row[2]) if row[2] else None,
                        "pb": float(row[3]) if row[3] else None,
                        "ps": float(row[4]) if row[4] else None,
                    })
                return result
            except Exception as e:
                logger.error(f"BaoStock获取历史估值异常: {e}")
                return []


    
    async def get_profit_data(self, code: str, year: int, quarter: int) -> Optional[Dict[str, Any]]:
        """获取盈利能力数据
        
        Args:
            code: 股票代码
            year: 年份
            quarter: 季度 (1-4)
            
        Returns:
            盈利能力指标字典，包含 roe_avg, np_margin, net_profit 等字段
            如果查询失败或数据不存在，返回 None
        """
        # 补全代码前缀
        if not code.startswith(("sh.", "sz.")):
            code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
        
        async with self.lock:
            try:
                rs = await asyncio.to_thread(bs.query_profit_data, code=code, year=year, quarter=quarter)
                
                if rs.error_code != "0":
                    # 尝试上一季度
                    if quarter > 1:
                        rs = await asyncio.to_thread(bs.query_profit_data, code=code, year=year, quarter=quarter-1)
                    else:
                        rs = await asyncio.to_thread(bs.query_profit_data, code=code, year=year-1, quarter=4)
                
                if rs.error_code != "0":
                    logger.error(f"BaoStock查询盈利能力失败: {rs.error_msg}")
                    return None
                
                def fetch_all(rs_obj):
                    data = []
                    while rs_obj.next():
                        data.append(rs_obj.get_row_data())
                    return data
                
                rows = await asyncio.to_thread(fetch_all, rs)
                
                if not rows:
                    return None
                
                row = rows[0]  # 取第一条
                return {
                    "code": row[0] if len(row) > 0 else code,
                    "pub_date": row[1] if len(row) > 1 else "",
                    "stat_date": row[2] if len(row) > 2 else "",
                    "roe_avg": float(row[3]) if len(row) > 3 and row[3] else None,
                    "np_margin": float(row[4]) if len(row) > 4 and row[4] else None,
                    "gp_margin": float(row[5]) if len(row) > 5 and row[5] else None,
                    "net_profit": float(row[6]) if len(row) > 6 and row[6] else None,
                    "eps_ttm": float(row[7]) if len(row) > 7 and row[7] else None,
                }
            except Exception as e:
                logger.error(f"BaoStock获取盈利能力异常: {e}")
                return None
