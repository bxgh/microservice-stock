import asyncio
from typing import Dict, Any, List, Optional
import baostock as bs
import numpy as np
from app.utils.logger import get_logger

logger = get_logger("baostock-api.service")

class BaoStockService:
    """包装 BaoStock 数据服务
    
    使用全局锁 (asyncio.Lock) 保证 BaoStock 单连接的线程安全性。
    所有同步 I/O 操作通过 asyncio.to_thread 在线程池中执行。
    """
    
    def __init__(self):
        self.lock = asyncio.Lock()
        self._is_logged_in = False
        
    def _login(self) -> bool:
        """同步执行登录逻辑"""
        try:
            lg = bs.login()
            if lg.error_code == "0":
                logger.info("BaoStock 登录成功")
                self._is_logged_in = True
                return True
            else:
                logger.error(f"BaoStock 登录失败: {lg.error_msg}")
                self._is_logged_in = False
                return False
        except Exception as e:
            logger.error(f"BaoStock 登录异常: {e}")
            self._is_logged_in = False
            return False

    async def _ensure_connection(self):
        """确保连接处于活跃状态，如果未登录则尝试登录"""
        if not self._is_logged_in:
            success = await asyncio.to_thread(self._login)
            if not success:
                logger.error("无法建立 BaoStock 连接")

    async def _execute_with_retry(self, func, *args, **kwargs):
        """执行 BaoStock 查询并带有自动重试机制"""
        async with self.lock:
            await self._ensure_connection()
            try:
                rs = await asyncio.to_thread(func, *args, **kwargs)
                
                # 检测连接类错误
                if rs.error_code != "0" and any(msg in rs.error_msg for msg in ["网络", "连接", "reset", "Broken pipe"]):
                    logger.warning(f"检测到连接问题({rs.error_msg})，尝试重新登录并重试...")
                    self._is_logged_in = False
                    await self._ensure_connection()
                    rs = await asyncio.to_thread(func, *args, **kwargs)
                
                return rs
            except Exception as e:
                if any(msg in str(e).lower() for msg in ["broken pipe", "connection", "reset"]):
                    logger.warning(f"捕获到连接异常: {e}，尝试重新登录并重试...")
                    self._is_logged_in = False
                    await self._ensure_connection()
                    try:
                        return await asyncio.to_thread(func, *args, **kwargs)
                    except Exception as re:
                        logger.error(f"重试后依然发生异常: {re}")
                        raise re
                raise e

    async def get_kline(
        self, 
        code: str, 
        frequency: str = "d", 
        adjust: str = "2", 
        start_date: str = "2020-01-01", 
        end_date: str = ""
    ) -> List[Dict[str, Any]]:
        """异步获取 K 线数据"""
        if not code.startswith(("sh.", "sz.")):
            code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
            
        try:
            rs = await self._execute_with_retry(
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
            
            return result[-500:] if len(result) > 500 else result
        except Exception as e:
            logger.error(f"BaoStock获取K线最终异常: {e}")
            return []

    async def get_index_cons(self, index_code: str) -> List[Dict[str, Any]]:
        """获取指数成分股"""
        try:
            # 标准化识别指数类型
            if index_code in ["sh.000300", "sz.399300"] or "300" in index_code:
                func = bs.query_hs300_stocks
            elif index_code in ["sh.000016"] or "50" in index_code:
                func = bs.query_sz50_stocks
            elif index_code in ["sh.000905", "sz.399005"] or "500" in index_code:
                func = bs.query_zz500_stocks
            else:
                logger.warning(f"不支持的指数代码: {index_code}")
                return []
            
            rs = await self._execute_with_retry(func)
            
            if rs.error_code != "0":
                return []
            
            def fetch_all(rs_obj):
                data = []
                while rs_obj.next():
                    data.append(rs_obj.get_row_data())
                return data
            
            rows = await asyncio.to_thread(fetch_all, rs)
            
            result = []
            for row in rows:
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
        try:
            rs = await self._execute_with_retry(bs.query_stock_industry)
            
            if rs.error_code != "0":
                logger.error(f"BaoStock查询行业分类失败: {rs.error_msg}")
                return []
            
            def fetch_all(rs_obj):
                data = []
                while rs_obj.next():
                    data.append(rs_obj.get_row_data())
                return data
            
            rows = await asyncio.to_thread(fetch_all, rs)
            
            industries = {}
            for row in rows:
                code = row[1] if len(row) > 1 else ""
                industry = row[3] if len(row) > 3 else ""
                if industry:
                    if industry not in industries:
                        industries[industry] = []
                    industries[industry].append(code)
            
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
    ) -> Dict[str, Any]:
        """获取历史估值数据 (PE/PB)"""
        if not code.startswith(("sh.", "sz.")):
            code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
            
        try:
            rs = await self._execute_with_retry(
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
                return {"history": [], "statistics": {}}
            
            def _fetch_all(rs_obj):
                data = []
                while rs_obj.next():
                    data.append(rs_obj.get_row_data())
                return data
            
            rows = await asyncio.to_thread(_fetch_all, rs)
            
            history = []
            for row in rows:
                history.append({
                    "date": row[0],
                    "price": float(row[1]) if row[1] else None,
                    "pe": float(row[2]) if row[2] else None,
                    "pb": float(row[3]) if row[3] else None,
                    "ps": float(row[4]) if row[4] else None,
                })
            
            # 计算统计指标
            pe_vals = [h['pe'] for h in history if h['pe'] is not None]
            pb_vals = [h['pb'] for h in history if h['pb'] is not None]
            ps_vals = [h['ps'] for h in history if h['ps'] is not None]
            
            stats = {}
            for key, vals in [("pe", pe_vals), ("pb", pb_vals), ("ps", ps_vals)]:
                if vals:
                    stats[key] = {
                        "mean": round(float(np.mean(vals)), 3),
                        "median": round(float(np.median(vals)), 3),
                        "min": round(float(np.min(vals)), 3),
                        "max": round(float(np.max(vals)), 3),
                        "p10": round(float(np.percentile(vals, 10)), 3),
                        "p25": round(float(np.percentile(vals, 25)), 3),
                        "p75": round(float(np.percentile(vals, 75)), 3),
                        "p90": round(float(np.percentile(vals, 90)), 3),
                        "current": vals[-1],
                        "percentile": round(float(np.sum(np.array(vals) < vals[-1]) / len(vals) * 100), 2) if len(vals) > 0 else None
                    }
                else:
                    stats[key] = None
                        
            return {
                "history": history,
                "statistics": stats
            }
        except Exception as e:
            logger.error(f"BaoStock获取历史估值异常: {e}")
            return {"history": [], "statistics": {}}

    async def get_profit_data(self, code: str, year: int, quarter: int) -> Optional[Dict[str, Any]]:
        """获取盈利能力数据"""
        if not code.startswith(("sh.", "sz.")):
            code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
        
        try:
            rs = await self._execute_with_retry(bs.query_profit_data, code=code, year=year, quarter=quarter)
            
            if rs.error_code != "0":
                # 尝试上一季度
                if quarter > 1:
                    rs = await self._execute_with_retry(bs.query_profit_data, code=code, year=year, quarter=quarter-1)
                else:
                    rs = await self._execute_with_retry(bs.query_profit_data, code=code, year=year-1, quarter=4)
            
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
            
            row = rows[0]
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
