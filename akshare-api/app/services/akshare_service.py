import asyncio
import math
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import akshare as ak
from app.utils.logger import get_logger

logger = get_logger("akshare-api.service")

class AkShareService:
    """AkShare 数据服务封装
    
    提供对 AkShare 库的异步封装，所有同步 I/O 操作通过 asyncio.to_thread 在线程池中执行。
    """
    
    def _clean_value(self, val: Any) -> Optional[float]:
        """清洗并转换数值（处理“1.2亿”, “-3.5%”, “NaN”, “None”等）"""
        if val is None or val is False:
            return None
            
        # 处理数值类型
        if isinstance(val, (int, float)):
            if math.isnan(val) or math.isinf(val):
                return None
            return float(val)
            
        s = str(val).strip()
        if not s or s.lower() in ['nan', 'none', 'false', '-', '--']:
            return None
            
        try:
            # 处理百分比
            multiplier = 1.0
            if s.endswith('%'):
                multiplier = 0.01
                s = s[:-1].strip()
            
            # 处理单位
            if s.endswith('亿'):
                multiplier *= 100000000
                s = s[:-1].strip()
            elif s.endswith('万'):
                multiplier *= 10000
                s = s[:-1].strip()
                
            final_val = float(s) * multiplier
            if math.isnan(final_val) or math.isinf(final_val):
                return None
            return final_val
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
                "pe": self._clean_value(row.get("市盈率-动态")),
                "pb": self._clean_value(row.get("市净率")),
                "market_cap": self._clean_value(row.get("总市值")),
                "price": self._clean_value(row.get("最新价")),
            }
        except Exception as e:
            logger.error(f"AkShare获取实时估值失败: symbol={symbol}, error={e}")
            return None

    async def get_lhb_detail(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """异步获取龙虎榜详情"""
        try:
            target_date = start_date
            
            # 如果未指定日期，自动获取最近一个交易日
            if not target_date:
                try:
                    trade_days = await asyncio.to_thread(ak.tool_trade_date_hist_sina)
                    if not trade_days.empty:
                        # 过滤掉未来的日期
                        today = date.today()
                        past_days = trade_days[trade_days['trade_date'] <= today]
                        if not past_days.empty:
                            target_date = str(past_days.iloc[-1]['trade_date'])
                        else:
                            target_date = datetime.now().strftime("%Y-%m-%d")
                except Exception as date_e:
                    logger.warning(f"获取交易日历失败，使用当前日期回退: {date_e}")
                    target_date = datetime.now().strftime("%Y-%m-%d")

            # 转换格式为 YYYYMMDD
            sd = target_date.replace("-", "")
            ed = (end_date or target_date).replace("-", "")
            
            logger.info(f"请求龙虎榜详情: start_date={sd}, end_date={ed}")
            df = await asyncio.to_thread(ak.stock_lhb_detail_em, start_date=sd, end_date=ed)
                
            if df is None or not hasattr(df, 'empty') or df.empty:
                logger.info(f"龙虎榜详情返回为空: {sd}")
                return []
                
            df = df.head(100) # 龙虎榜数据通常较多，适当增加条数
            result = []
            for _, row in df.iterrows():
                result.append({
                    "code": row.get("代码", ""),
                    "name": row.get("名称", ""),
                    "close": self._clean_value(row.get("收盘价")),
                    "change_pct": self._clean_value(row.get("涨跌幅")),
                    "turnover_rate": self._clean_value(row.get("换手率")),
                    "net_buy": self._clean_value(row.get("龙虎榜净买额")),
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
                    "price": self._clean_value(row.get("最新价")),
                    "change_pct": self._clean_value(row.get("涨跌幅")),
                    "volume": self._clean_value(row.get("成交量")),
                    "amount": self._clean_value(row.get("成交额")),
                    "turnover_rate": self._clean_value(row.get("换手率")),
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取热门排行失败: error={e}")
            return []
