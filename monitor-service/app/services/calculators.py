import numpy as np
import pandas as pd
import logging
from typing import List, Dict, Any
from app.utils.database import db

logger = logging.getLogger("monitor-service.calculators")

class ScoreCalculator:
    """分位数评分计算器，用于将原始值转换为 0-100 的得分"""
    
    async def get_percentile_score(self, indicator_name: str, current_value: float, target_date: str, lookback_days: int = 750) -> float:
        """
        根据历史 lookback_days (约 3 年) 的数据计算当前值的分位数
        """
        # 获取历史分布 (排除当前及未来日期，确保回测准确性)
        query = """
            SELECT indicator_value FROM monitor_indicators_history 
            WHERE indicator_name = %s AND trade_date < %s
            ORDER BY trade_date DESC LIMIT %s
        """
        rows = await db.execute(query, (indicator_name, target_date, lookback_days))
        if not rows or len(rows) < 20:
            return 50.0 # 数据不足，返回中性分
            
        history = [r[0] for r in rows if r[0] is not None]
        history.append(current_value)
        
        # 使用 rank 方式计算
        history_series = pd.Series(history)
        rank = history_series.rank(pct=True).iloc[-1]
        
        return float(rank * 100)

class DispersionCalculator:
    """行业与宽基指数分化度计算器"""
    
    async def calculate_industry_dispersion(self, target_date: str) -> float:
        """
        计算指定日期的行业分化度 (截面标准差)
        """
        query = """
            SELECT t1.ts_code, (t1.close - t2.close) / t2.close as pct_chg
            FROM raw_sector_daily t1
            JOIN raw_sector_daily t2 ON t1.ts_code = t2.ts_code
            WHERE t1.trade_date = %s 
            AND t2.trade_date = (
                SELECT MAX(trade_date) FROM raw_sector_daily 
                WHERE trade_date < %s AND ts_code = t1.ts_code
            )
            AND t1.ts_code LIKE '801%%'
        """
        rows = await db.execute(query, (target_date, target_date))
        if not rows or len(rows) < 10:
            return 0.0
            
        pct_changes = [r[1] for r in rows if r[1] is not None]
        if not pct_changes:
            return 0.0
            
        return float(np.std(pct_changes))

class BreadthCalculator:
    """市场宽度与赚钱效应计算器"""
    
    async def calculate_ad_ratio(self, target_date: str) -> float:
        """计算涨跌家数比"""
        query = "SELECT advance_count, decline_count FROM raw_market_stats WHERE trade_date = %s"
        rows = await db.execute(query, (target_date,))
        if not rows:
            return 0.5
            
        adv, dec = rows[0]
        if (adv + dec) == 0:
            return 0.5
        return adv / (adv + dec)

class RelativeStrengthCalculator:
    """新旧经济相对强度计算器"""
    
    async def calculate_growth_value_ratio(self, target_date: str, growth_codes: List[str], value_codes: List[str]) -> float:
        """计算 (成长ETF均值 / 价值ETF均值) 的相对强度"""
        all_codes = growth_codes + value_codes
        query = "SELECT ts_code, close FROM raw_sector_daily WHERE trade_date = %s AND ts_code IN %s"
        rows = await db.execute(query, (target_date, tuple(all_codes)))
        
        if not rows:
            return 1.0
            
        price_map = {r[0]: r[1] for r in rows}
        growth_prices = [price_map[c] for c in growth_codes if c in price_map]
        value_prices = [price_map[c] for c in value_codes if c in price_map]
        
        if not growth_prices or not value_prices:
            return 1.0
            
        return float(np.mean(growth_prices) / np.mean(value_prices))

class FundsCalculator:
    """资金面核心指标计算器 (龙虎榜、大宗、两融)"""
    
    async def calculate_lhb_net_buy(self, target_date: str) -> float:
        """计算当日龙虎榜全市场净买入额"""
        query = "SELECT SUM(net_buy_amt) FROM stock_lhb_daily WHERE trade_date = %s"
        rows = await db.execute(query, (target_date,))
        return float(rows[0][0]) if rows and rows[0][0] else 0.0

    async def calculate_block_trade_amount(self, target_date: str) -> float:
        """计算当日大宗交易总成交额"""
        query = "SELECT SUM(amount) FROM stock_block_trade WHERE trade_date = %s"
        rows = await db.execute(query, (target_date,))
        return float(rows[0][0]) if rows and rows[0][0] else 0.0

    async def calculate_margin_buy(self, target_date: str) -> float:
        """计算当日融资买入额"""
        query = "SELECT margin_buy FROM market_margin_summary WHERE trade_date = %s"
        rows = await db.execute(query, (target_date,))
        return float(rows[0][0]) if rows and rows[0][0] else 0.0

class MonitorEngine:
    """监控引擎主类，负责调度计算并存储指标"""
    
    def __init__(self):
        self.disp_calc = DispersionCalculator()
        self.breadth_calc = BreadthCalculator()
        self.rs_calc = RelativeStrengthCalculator()
        self.score_calc = ScoreCalculator()
        self.funds_calc = FundsCalculator()

    async def run_daily_calculation(self, target_date: str):
        """执行每日指标测算"""
        logger.info(f"开始测算日期 {target_date} 的监控指标...")
        
        # 1. 计算各项基础指标
        industry_disp = await self.disp_calc.calculate_industry_dispersion(target_date)
        
        ad_ratio = await self.breadth_calc.calculate_ad_ratio(target_date)
        if ad_ratio == 0.5:
            ad_ratio = await self._calculate_sector_breadth_proxy(target_date)
            
        from app.core.config import settings
        gv_ratio = await self.rs_calc.calculate_growth_value_ratio(
            target_date, 
            settings.GROWTH_ETFS, 
            settings.VALUE_ETFS
        )
        
        query_north = """
            SELECT SUM(north_net_inflow) FROM raw_capital_flow_summary 
            WHERE trade_date <= %s AND trade_date >= DATE_SUB(%s, INTERVAL 10 DAY)
            ORDER BY trade_date DESC LIMIT 5
        """
        rows = await db.execute(query_north, (target_date, target_date))
        north_momentum = float(rows[0][0]) if rows and rows[0][0] else 0.0
        
        # 2. 计算新增资金面指标
        lhb_net_buy = await self.funds_calc.calculate_lhb_net_buy(target_date)
        bt_amount = await self.funds_calc.calculate_block_trade_amount(target_date)
        margin_buy = await self.funds_calc.calculate_margin_buy(target_date)
        
        # 3. 存储原始值
        raw_indicators = [
            ('industry_dispersion', industry_disp),
            ('market_breadth', ad_ratio),
            ('growth_value_ratio', gv_ratio),
            ('north_funds_momentum', north_momentum),
            ('lhb_net_buy', lhb_net_buy),
            ('block_trade_amount', bt_amount),
            ('margin_buy_amount', margin_buy)
        ]
        
        for name, val in raw_indicators:
            query_insert = """
                INSERT INTO monitor_indicators_history (trade_date, indicator_name, indicator_value)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE indicator_value=VALUES(indicator_value)
            """
            await db.execute(query_insert, (target_date, name, val))
        
        # 3. 计算得分
        for name, val in raw_indicators:
            score = await self.score_calc.get_percentile_score(name, val, target_date)
            await db.execute(
                "UPDATE monitor_indicators_history SET score = %s WHERE trade_date = %s AND indicator_name = %s",
                (score, target_date, name)
            )
            
        # 4. 综合评分
        scores_rows = await db.execute(
            "SELECT indicator_name, score FROM monitor_indicators_history WHERE trade_date = %s",
            (target_date,)
        )
        scores_dict = {r[0]: r[1] for r in scores_rows if r[1] is not None}
        
        if len(scores_dict) >= 5:
            # 权重重新分配: 宽度(20%) + 北向(20%) + 游资/大宗(25%) + 杠杆(15%) + 结构/分化(20%)
            total_score = (
                scores_dict.get('market_breadth', 50) * 0.20 +
                scores_dict.get('north_funds_momentum', 50) * 0.20 +
                scores_dict.get('lhb_net_buy', 50) * 0.15 +
                scores_dict.get('block_trade_amount', 50) * 0.10 +
                scores_dict.get('margin_buy_amount', 50) * 0.15 +
                scores_dict.get('industry_dispersion', 50) * 0.10 +
                scores_dict.get('growth_value_ratio', 50) * 0.10
            )
            
            status = 'NORMAL'
            if total_score > 80: status = 'BULL_FEVER'
            elif total_score > 65: status = 'BULL_ALERT'
            elif total_score < 35: status = 'BEAR_ALERT'

            await db.execute("""
                INSERT INTO monitor_health_scores (trade_date, total_score, status)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE total_score=VALUES(total_score), status=VALUES(status)
            """, (target_date, total_score, status))

            logger.info(f"日期 {target_date} 指标与综合评分测算完成。总体分: {total_score:.2f}")

    async def _calculate_sector_breadth_proxy(self, target_date: str) -> float:
        """行业广度代理指标"""
        query = """
            SELECT COUNT(*) FROM raw_sector_daily t1
            JOIN raw_sector_daily t2 ON t1.ts_code = t2.ts_code
            WHERE t1.trade_date = %s 
            AND t2.trade_date = (SELECT MAX(trade_date) FROM raw_sector_daily WHERE trade_date < %s AND ts_code = t1.ts_code)
            AND t1.close > t2.close
            AND t1.ts_code LIKE '801%%'
        """
        rows = await db.execute(query, (target_date, target_date))
        adv_sectors = rows[0][0] if rows else 0
        return adv_sectors / 31.0

monitor_engine = MonitorEngine()

monitor_engine = MonitorEngine()
