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
                        "date": str(r["report_date"]), "analyst": r["analyst"], "rating": r["rating"], 
                        "change": r["change_direction"], "target_price": float(r["target_price"]) if r["target_price"] else None
                    } for r in ranks
                ],
                "forecasts": [
                    {
                        "notice_date": str(f["notice_date"]), "period": str(f["report_period"]), "type": f["type"],
                        "growth_min": float(f["growth_min"]) if f["growth_min"] else None,
                        "growth_max": float(f["growth_max"]) if f["growth_max"] else None
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
                        "period": str(i["report_date"]), "total_revenue": float(i["total_revenue"]) if i["total_revenue"] else None,
                        "net_profit": float(i["net_profit"]) if i["net_profit"] else None
                    } for i in income
                ],
                "indicators": [
                    {
                        "period": str(ind["report_date"]), "roe": float(ind["roe"]) if ind["roe"] else None,
                        "gross_margin": float(ind["grossprofit_margin"]) if ind["grossprofit_margin"] else None,
                        "eps": float(ind["eps"]) if ind["eps"] else None
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
                        "date": str(c["end_date"]), "count": c["holder_count"], 
                        "change_pct": float(c["holder_change_pct"]) if c["holder_change_pct"] else None
                    } for c in counts
                ],
                "top10": [
                    {
                        "rank": t["rank"], "name": t["holder_name"], "type": t["share_type"], 
                        "count": t["hold_count"], "pct": float(t["hold_pct"]) if t["hold_pct"] else None
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
                        "date": str(n["trade_date"]), "count": n["hold_count"], "ratio": float(n["hold_ratio"]) if n["hold_ratio"] else None
                    } for n in north
                ],
                "lhb": [
                    {
                        "date": str(l["trade_date"]), "close": float(l["close_price"]) if l["close_price"] else None,
                        "change": float(l["change_pct"]) if l["change_pct"] else None,
                        "net_buy": float(l["net_buy_amt"]) if l["net_buy_amt"] else None,
                        "reason": l["reason"]
                    } for l in lhb
                ]
            }
        except Exception as e:
            logger.error(f"获取资金数据失败: {e}")
            return {"north_funds": [], "lhb": []}

    async def search_stocks(self, keyword: str, limit: int = 15) -> List[Dict[str, Any]]:
        """股票模糊搜索 (代码、名称、拼音)"""
        try:
            # 核心逻辑:
            # 1. 优先查询专门为搜索优化的 stock_info (含拼音索引)
            # 2. 如果结果为空且输入是数字代码，则回退查询全量基础信息表 stock_basic_info
            
            search_pattern = f"{keyword}%" if keyword.isdigit() else f"%{keyword}%"
            fuzzy_pattern = f"%{keyword}%"
            
            # 第一阶段: 查询 stock_info (高性能搜索表)
            sql_info = """
                SELECT ts_code, symbol, name, market, industry_sw as industry, status
                FROM stock_info 
                WHERE (ts_code LIKE %s OR symbol LIKE %s OR name LIKE %s OR pinyin_initial LIKE %s)
                ORDER BY 
                    (CASE WHEN symbol = %s THEN 0 
                          WHEN symbol LIKE %s THEN 1
                          WHEN name = %s THEN 2
                          ELSE 3 END),
                    status DESC, ts_code ASC
                LIMIT %s
            """
            params = (search_pattern, search_pattern, fuzzy_pattern, fuzzy_pattern, keyword, search_pattern, keyword, limit)
            results = await db.execute(sql_info, params)
            
            # 第二阶段回退: 如果 stock_info 没搜到且是数字，查全量基础库 stock_basic_info
            if not results and keyword.isdigit():
                sql_basic = """
                    SELECT ts_code, symbol, name, market, '' as industry, 1 as status
                    FROM stock_basic_info
                    WHERE symbol LIKE %s OR ts_code LIKE %s
                    LIMIT %s
                """
                results = await db.execute(sql_basic, (search_pattern, search_pattern, limit))
            
            # 格式转换
            return [
                {
                    "tsCode": r["ts_code"],
                    "symbol": r["symbol"],
                    "name": r["name"],
                    "market": r["market"],
                    "industry": r["industry"],
                    "status": "normal" if r["status"] == 1 else ("halt" if r["status"] == 2 else ("st" if r["status"] == 3 else "delisted"))
                } for r in results
            ]
        except Exception as e:
            logger.error(f"搜索股票失败: {e}")
            return []

stock_info_service = StockInfoService()
