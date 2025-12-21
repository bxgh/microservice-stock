import asyncio
from typing import Dict, Any, List, Optional
import akshare as ak
from app.utils.logger import get_logger

logger = get_logger("akshare-api.service")

class AkShareService:
    """AkShare 数据服务封装
    
    提供对 AkShare 库的异步封装，所有同步 I/O 操作通过 asyncio.to_thread 在线程池中执行。
    """
    
    def _clean_value(self, val: Any) -> Optional[float]:
        """清洗并转换数值（处理“1.2亿”, “-3.5%”, “None”等）"""
        if val is None or val is False or str(val).lower() == 'nan' or str(val).lower() == 'none' or str(val).lower() == 'false':
            return None
            
        s = str(val).strip()
        if not s:
            return None
            
        try:
            # 处理百分比
            multiplier = 1.0
            if s.endswith('%'):
                multiplier = 0.01
                s = s[:-1]
            
            # 处理单位
            if s.endswith('亿'):
                multiplier *= 100000000
                s = s[:-1]
            elif s.endswith('万'):
                multiplier *= 10000
                s = s[:-1]
                
            return float(s) * multiplier
        except (ValueError, TypeError):
            return None

    async def get_financial_abstract(self, symbol: str) -> Optional[Dict[str, Any]]:
        """异步获取财务摘要
        
        支持多种 AkShare 返回格式（长格式、宽格式、中英文指标名）。
        """
        try:
            df = await asyncio.to_thread(ak.stock_financial_abstract_ths, symbol=symbol)
            
            if df is None or df.empty:
                return None
            
            result = {
                "total_revenue": None,
                "net_profit": None,
                "roe": None,
                "report_date": None,
            }

            # 格式 A: 长格式 (report_date, metric_name, value ...)
            if 'metric_name' in df.columns and 'value' in df.columns:
                latest_report = df['report_date'].iloc[0] if 'report_date' in df.columns else None
                result["report_date"] = str(latest_report) if latest_report else None
                
                # 指标映射 (英文 -> 结果键)
                mapping = {
                    'operating_income_total': 'total_revenue',
                    'parent_holder_net_profit': 'net_profit',
                    'index_weighted_avg_roe': 'roe',
                }
                
                for _, row in df.iterrows():
                    m_name = row.get('metric_name')
                    if m_name in mapping:
                        result[mapping[m_name]] = self._clean_value(row.get('value'))

            # 格式 B: 宽格式 (报告期, 营业总收入, 净利润 ...)
            else:
                # 确定最新一行（通常是首行或尾行，根据日期判断）
                # 为了稳妥，按日期排序
                date_col = '报告期' if '报告期' in df.columns else ('report_date' if 'report_date' in df.columns else None)
                if date_col:
                    df = df.sort_values(by=date_col, ascending=False)
                    latest = df.iloc[0]
                    result["report_date"] = str(latest[date_col])
                    
                    # 字段映射 (中文 -> 结果键)
                    mapping = {
                        '营业总收入': 'total_revenue',
                        '净利润': 'net_profit',
                        '净资产收益率': 'roe',
                    }
                    
                    for cn_name, key in mapping.items():
                        if cn_name in df.columns:
                            result[key] = self._clean_value(latest[cn_name])

            return result
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
