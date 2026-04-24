import datetime
from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("gateway.stock_info_service")

class StockInfoService:
    """个股详细信息服务 (基本面、财务、资金、股东)"""

    async def get_fundamentals(self, code: str) -> Dict[str, Any]:
        """获取个股基本面信息 (评级、预告、情感)"""
        try:
            # 1. 机构评级
            sql_rank = """
                SELECT report_date, analyst, rating, change_direction, target_price 
                FROM stock_analyst_rank 
                WHERE stock_code = %s 
                ORDER BY report_date DESC LIMIT 10
            """
            ranks = await db.execute(sql_rank, (code,))
            
            # 2. 业绩预告
            sql_forecast = """
                SELECT notice_date, report_period, type, growth_min, growth_max 
                FROM stock_performance_forecast 
                WHERE stock_code = %s 
                ORDER BY report_period DESC LIMIT 5
            """
            forecasts = await db.execute(sql_forecast, (code,))

            return {
                "analyst_ranks": [
                    {
                        "date": str(r[0]), "analyst": r[1], "rating": r[2], 
                        "change": r[3], "target_price": float(r[4]) if r[4] else None
                    } for r in ranks
                ],
                "forecasts": [
                    {
                        "notice_date": str(f[0]), "period": str(f[1]), "type": f[2],
                        "growth_min": float(f[3]) if f[3] else None,
                        "growth_max": float(f[4]) if f[4] else None
                    } for f in forecasts
                ]
            }
        except Exception as e:
            logger.error(f"获取基本面数据失败: {e}")
            return {"analyst_ranks": [], "forecasts": []}

    async def get_financials(self, code: str, limit: int = 4) -> Dict[str, Any]:
        """获取个股财务报表与指标"""
        try:
            # 1. 利润表 (最近4期)
            sql_income = """
                SELECT report_date, total_revenue, operating_revenue, net_profit, parent_net_profit 
                FROM stock_income_statement 
                WHERE ts_code = %s 
                ORDER BY report_date DESC LIMIT %s
            """
            income = await db.execute(sql_income, (code, limit))

            # 2. 财务指标
            sql_indicators = """
                SELECT report_date, roe, grossprofit_margin, netprofit_margin, asset_liab_ratio, eps 
                FROM stock_finance_indicators 
                WHERE ts_code = %s 
                ORDER BY report_date DESC LIMIT %s
            """
            indicators = await db.execute(sql_indicators, (code, limit))

            return {
                "income_statements": [
                    {
                        "period": str(i[0]), "total_revenue": float(i[1]) if i[1] else None,
                        "net_profit": float(i[3]) if i[3] else None
                    } for i in income
                ],
                "indicators": [
                    {
                        "period": str(ind[0]), "roe": float(ind[1]) if ind[1] else None,
                        "gross_margin": float(ind[2]) if ind[2] else None,
                        "eps": float(ind[5]) if ind[5] else None
                    } for ind in indicators
                ]
            }
        except Exception as e:
            logger.error(f"获取财务数据失败: {e}")
            return {"income_statements": [], "indicators": []}

    async def get_shareholders(self, code: str) -> Dict[str, Any]:
        """获取个股股东信息"""
        try:
            # 1. 股东户数
            sql_count = """
                SELECT end_date, holder_count, holder_change_pct, avg_market_cap 
                FROM stock_shareholder_count 
                WHERE ts_code = %s 
                ORDER BY end_date DESC LIMIT 10
            """
            counts = await db.execute(sql_count, (code,))

            # 2. 前十大股东 (最新一期)
            sql_top10 = """
                SELECT end_date, rank, holder_name, share_type, hold_count, hold_pct 
                FROM stock_top10_shareholders 
                WHERE ts_code = %s AND end_date = (
                    SELECT MAX(end_date) FROM stock_top10_shareholders WHERE ts_code = %s
                )
                ORDER BY rank ASC
            """
            top10 = await db.execute(sql_top10, (code, code))

            return {
                "holder_counts": [
                    {
                        "date": str(c[0]), "count": c[1], 
                        "change_pct": float(c[2]) if c[2] else None
                    } for c in counts
                ],
                "top10": [
                    {
                        "rank": t[1], "name": t[2], "type": t[3], 
                        "count": t[4], "pct": float(t[5]) if t[5] else None
                    } for t in top10
                ]
            }
        except Exception as e:
            logger.error(f"获取股东数据失败: {e}")
            return {"holder_counts": [], "top10": []}

    async def get_funds(self, code: str) -> Dict[str, Any]:
        """获取个股资金流向 (北向、龙虎榜、大宗)"""
        try:
            # 1. 北向持股 (最近10日)
            sql_north = """
                SELECT trade_date, hold_count, hold_ratio 
                FROM stock_north_funds_daily 
                WHERE ts_code = %s 
                ORDER BY trade_date DESC LIMIT 10
            """
            north = await db.execute(sql_north, (code,))

            # 2. 龙虎榜 (最近记录)
            sql_lhb = """
                SELECT trade_date, close_price, change_pct, net_buy_amt, reason 
                FROM stock_lhb_daily 
                WHERE ts_code = %s 
                ORDER BY trade_date DESC LIMIT 5
            """
            lhb = await db.execute(sql_lhb, (code,))

            return {
                "north_funds": [
                    {
                        "date": str(n[0]), "count": n[1], "ratio": float(n[2]) if n[2] else None
                    } for n in north
                ],
                "lhb": [
                    {
                        "date": str(l[0]), "close": float(l[1]) if l[1] else None,
                        "change": float(l[2]) if l[2] else None,
                        "net_buy": float(l[3]) if l[3] else None,
                        "reason": l[4]
                    } for l in lhb
                ]
            }
        except Exception as e:
            logger.error(f"获取资金数据失败: {e}")
            return {"north_funds": [], "lhb": []}

stock_info_service = StockInfoService()
