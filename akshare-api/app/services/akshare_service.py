import asyncio
from typing import Dict, Any, List, Optional
import akshare as ak
from app.utils.logger import get_logger

logger = get_logger("akshare-api.service")

class AkShareService:
    """AkShare 数据服务封装
    
    提供对 AkShare 库的异步封装，所有同步 I/O 操作通过 asyncio.to_thread 在线程池中执行。
    """
    
    async def get_financial_abstract(self, symbol: str) -> Optional[Dict[str, Any]]:
        """异步获取财务摘要
        
        Args:
            symbol: 股票代码，如 "600519"
            
        Returns:
            财务摘要字典，包含 total_revenue, net_profit, roe, report_date 字段
            如果查询失败或数据不存在，返回 None
            
        Example:
            >>> service = AkShareService()
            >>> result = await service.get_financial_abstract("600519")
            >>> print(result["net_profit"])
        """
        try:
            # 使用 to_thread 在线程池中执行同步 I/O 库
            df = await asyncio.to_thread(ak.stock_financial_abstract_ths, symbol=symbol)
            
            if df is None or df.empty:
                return None
            
            # AkShare 返回长格式数据，每行是一个指标
            # 提取最新报告期的数据
            latest_report = df['report_date'].iloc[0] if 'report_date' in df.columns else None
            
            # 创建指标映射字典
            metrics = {}
            for _, row in df.iterrows():
                metric_name = row.get('metric_name', '')
                value = row.get('value')
                metrics[metric_name] = value
            
            # 提取关键财务指标（根据 AkShare 实际字段名）
            return {
                "total_revenue": metrics.get('operating_income_total'),  # 营业总收入
                "net_profit": metrics.get('parent_holder_net_profit'),  # 净利润（归母）
                "roe": metrics.get('index_weighted_avg_roe'),  # 加权平均ROE
                "report_date": str(latest_report) if latest_report else None,
            }
        except Exception as e:
            logger.error(f"AkShare获取财务摘要失败: symbol={symbol}, error={e}")
            return None

    async def get_valuation_spot(self, symbol: str) -> Optional[Dict[str, Any]]:
        """异步获取实时估值
        
        Args:
            symbol: 股票代码，如 "600519"
            
        Returns:
            实时估值字典，包含 name, pe, pb, market_cap, price 字段
            如果查询失败或股票不存在，返回 None
        """
        try:
            df = await asyncio.to_thread(ak.stock_zh_a_spot_em)
            
            if df is None or df.empty:
                return None
                
            stock = df[df["代码"] == symbol]
            if stock.empty:
                return None
                
            row = stock.iloc[0]
            return {
                "name": row.get("名称", ""),
                "pe": float(row.get("市盈率-动态", 0)) if row.get("市盈率-动态") else None,
                "pb": float(row.get("市净率", 0)) if row.get("市净率") else None,
                "market_cap": float(row.get("总市值", 0)) if row.get("总市值") else None,
                "price": float(row.get("最新价", 0)) if row.get("最新价") else None,
            }
        except Exception as e:
            logger.error(f"AkShare获取实时估值失败: symbol={symbol}, error={e}")
            return None

    async def get_valuation_history(self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """异步获取历史估值指标"""
        try:
            df = await asyncio.to_thread(ak.stock_a_lg_indicator, symbol=symbol)
            
            if df is None or df.empty:
                return []
                
            if start_date:
                df = df[df["trade_date"] >= start_date]
            if end_date:
                df = df[df["trade_date"] <= end_date]
                
            # 限制返回数量以保证性能
            df = df.head(100)
            
            result = []
            for _, row in df.iterrows():
                result.append({
                    "date": str(row.get("trade_date", "")),
                    "pe": float(row.get("pe", 0)) if row.get("pe") else None,
                    "pe_ttm": float(row.get("pe_ttm", 0)) if row.get("pe_ttm") else None,
                    "pb": float(row.get("pb", 0)) if row.get("pb") else None,
                    "ps": float(row.get("ps", 0)) if row.get("ps") else None,
                    "ps_ttm": float(row.get("ps_ttm", 0)) if row.get("ps_ttm") else None,
                    "total_mv": float(row.get("total_mv", 0)) if row.get("total_mv") else None,
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取历史估值失败: symbol={symbol}, error={e}")
            return []

    async def get_lhb_detail(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """异步获取龙虎榜详情
        
        Args:
            start_date: 开始日期，格式 YYYY-MM-DD，可选
            end_date: 结束日期，格式 YYYY-MM-DD，可选
            
        Returns:
            龙虎榜记录列表，每条记录包含 code, name, close, change_pct 等字段
            最多返回 50 条记录
        """
        try:
            if start_date and end_date:
                sd = start_date.replace("-", "")
                ed = end_date.replace("-", "")
                df = await asyncio.to_thread(ak.stock_lhb_detail_em, start_date=sd, end_date=ed)
            else:
                df = await asyncio.to_thread(ak.stock_lhb_detail_em)
                
            if df is None or df.empty:
                return []
                
            df = df.head(50)
            result = []
            for _, row in df.iterrows():
                result.append({
                    "code": row.get("代码", ""),
                    "name": row.get("名称", ""),
                    "close": float(row.get("收盘价", 0)) if row.get("收盘价") else None,
                    "change_pct": float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                    "turnover_rate": float(row.get("换手率", 0)) if row.get("换手率") else None,
                    "net_buy": float(row.get("龙虎榜净买额", 0)) if row.get("龙虎榜净买额") else None,
                    "reason": row.get("上榜原因", ""),
                    "date": str(row.get("上榜日", "")),
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取龙虎榜失败: error={e}")
            return []

    async def get_individual_info(self, symbol: str) -> Dict[str, Any]:
        """异步获取个股详情"""
        try:
            df = await asyncio.to_thread(ak.stock_individual_info_em, symbol=symbol)
            if df is None or df.empty:
                return {}
                
            info = {}
            for _, row in df.iterrows():
                item = row.get("item", "")
                value = row.get("value", "")
                if item == "行业": info["industry"] = value
                elif item == "股票简称": info["name"] = value
                elif item == "上市时间": info["list_date"] = value
                elif item == "总股本": info["total_share"] = value
            return info
        except Exception as e:
            logger.error(f"AkShare获取个股信息失败: symbol={symbol}, error={e}")
            return {}

    async def get_hot_rank(self, limit: int = 50) -> List[Dict[str, Any]]:
        """异步获取热门排行(以成交额为准)
        
        Args:
            limit: 返回数量限制，默认 50
            
        Returns:
            热门股票列表，按成交额降序排列
            每条记录包含 code, name, price, change_pct, volume, amount 等字段
        """
        try:
            df = await asyncio.to_thread(ak.stock_zh_a_spot_em)
            if df is None or df.empty:
                return []
                
            df = df.sort_values("成交额", ascending=False).head(limit)
            result = []
            for _, row in df.iterrows():
                result.append({
                    "code": row.get("代码", ""),
                    "name": row.get("名称", ""),
                    "price": float(row.get("最新价", 0)) if row.get("最新价") else None,
                    "change_pct": float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                    "volume": float(row.get("成交量", 0)) if row.get("成交量") else None,
                    "amount": float(row.get("成交额", 0)) if row.get("成交额") else None,
                    "turnover_rate": float(row.get("换手率", 0)) if row.get("换手率") else None,
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取热门排行失败: error={e}")
            return []
