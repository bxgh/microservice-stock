import asyncio
import httpx
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger("stock-manager.market_data")

class MarketDataService:
    def __init__(self):
        self.tushare_url = settings.TUSHARE_API_URL
        self.akshare_url = settings.AKSHARE_API_URL

    async def sync_index_basic(self, market: str = ''):
        """从 Tushare 同步指数基础信息到 index_basic"""
        try:
            url = f"{self.tushare_url}/api/v1/index/basic"
            params = {"market": market}
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json().get("data", [])
            
            if not data:
                logger.warning("未获取到指数基础信息")
                return 0

            query = """
                INSERT INTO index_basic (
                    ts_code, name, fullname, market, publisher, 
                    index_type, category, base_date, base_point, 
                    list_date, weight_rule, description, exp_date
                ) VALUES (
                    %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, 
                    %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                name=VALUES(name), fullname=VALUES(fullname), market=VALUES(market),
                publisher=VALUES(publisher), index_type=VALUES(index_type),
                category=VALUES(category), base_date=VALUES(base_date),
                base_point=VALUES(base_point), list_date=VALUES(list_date),
                weight_rule=VALUES(weight_rule), description=VALUES(description),
                exp_date=VALUES(exp_date)
            """
            args = []
            for i in data:
                args.append((
                    i.get("ts_code"), i.get("name"), i.get("fullname"), i.get("market"), i.get("publisher"),
                    i.get("index_type"), i.get("category"), i.get("base_date"), i.get("base_point"),
                    i.get("list_date"), i.get("weight_rule"), i.get("desc"), i.get("exp_date")
                ))
            
            await db.execute_many(query, args)
            logger.info(f"成功同步指数基础信息: {len(args)} 条")
            return len(args)
        except Exception as e:
            logger.error(f"同步指数基础信息失败: {e}")
            raise

    async def sync_stock_daily(self, ts_code: str = '', trade_date: str = '', start_date: str = '', end_date: str = ''):
        """从 Tushare 同步股票日线行情到 stock_kline_daily"""
        try:
            url = f"{self.tushare_url}/api/v1/stock/daily"
            params = {
                "ts_code": ts_code,
                "trade_date": trade_date.replace("-", ""),
                "start_date": start_date.replace("-", ""),
                "end_date": end_date.replace("-", "")
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json().get("data", [])
            
            if not data:
                return 0

            query = """
                INSERT INTO stock_kline_daily (
                    code, trade_date, open, high, low, close, 
                    pre_close, pct_chg, volume, amount
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                open=VALUES(open), high=VALUES(high), low=VALUES(low),
                close=VALUES(close), pre_close=VALUES(pre_close),
                pct_chg=VALUES(pct_chg), volume=VALUES(volume), amount=VALUES(amount)
            """
            args = []
            for i in data:
                d = i.get("trade_date")
                dt_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
                # Tushare pct_chg 是百分比，转为小数
                pct_chg = float(i.get("pct_chg", 0)) / 100.0 if i.get("pct_chg") is not None else None
                
                args.append((
                    i.get("ts_code"), dt_str, i.get("open"), i.get("high"), i.get("low"), i.get("close"),
                    i.get("pre_close"), pct_chg, i.get("vol"), 
                    float(i.get("amount", 0)) * 1000.0 if i.get("amount") is not None else None
                ))
            
            await db.execute_many(query, args)
            logger.info(f"同步股票日线 [{trade_date or ts_code}]: {len(args)} 条")
            return len(args)
        except Exception as e:
            logger.error(f"同步股票日线失败: {ts_code or trade_date}, {e}")
            raise

    async def sync_index_daily(self, ts_code: str, start_date: str = '', end_date: str = '', trade_date: str = ''):
        """从 Tushare 同步指数日线行情到 ods_index_daily"""
        try:
            url = f"{self.tushare_url}/api/v1/index/daily"
            params = {
                "ts_code": ts_code,
                "start_date": start_date.replace("-", ""),
                "end_date": end_date.replace("-", ""),
                "trade_date": trade_date.replace("-", "")
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json().get("data", [])

            if not data:
                return 0

            query = """
                INSERT INTO ods_index_daily (
                    trade_date, ts_code, open, high, low, close, 
                    pre_close, `change`, pct_chg, vol, amount
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                open=VALUES(open), high=VALUES(high), low=VALUES(low),
                close=VALUES(close), pre_close=VALUES(pre_close),
                `change`=VALUES(`change`), pct_chg=VALUES(pct_chg),
                vol=VALUES(vol), amount=VALUES(amount)
            """
            args = []
            for i in data:
                # 转换日期格式 '20260425' -> '2026-04-25'
                d = i.get("trade_date")
                dt_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
                
                # Tushare pct_chg 是百分比，转为小数
                pct_chg = float(i.get("pct_chg", 0)) / 100.0 if i.get("pct_chg") is not None else None
                
                args.append((
                    dt_str, i.get("ts_code"), i.get("open"), i.get("high"), i.get("low"), i.get("close"),
                    i.get("pre_close"), i.get("change"), pct_chg, i.get("vol"), 
                    float(i.get("amount", 0)) * 1000.0 if i.get("amount") is not None else None
                ))

            await db.execute_many(query, args)
            return len(args)
        except Exception as e:
            logger.error(f"同步指数日线失败: {ts_code}, {e}")
            raise

    async def sync_market_breadth_daily(self, target_date: str):
        """计算并同步当日市场广度到 ods_market_breadth_daily"""
        try:
            # 1. 从 stock_kline_daily 聚合
            # 剔除 B 股 (代码以 900 或 200 开头), 剔除新股 (上市 < 60天) - 简化逻辑：只取主板创业板科创板
            # 剔除长期停牌由 stock_kline_daily 的存在性自然保证(当日无成交不出现在该表或 vol=0)
            
            # 先获取总数 (在市且非新股)
            # 假设 stock_basic_info 有 list_date
            sql_count = """
                SELECT COUNT(*) FROM stock_basic_info 
                WHERE list_status = 'L' 
                AND list_date <= DATE_SUB(%s, INTERVAL 60 DAY)
                AND ts_code NOT LIKE '900%%' AND ts_code NOT LIKE '200%%'
            """
            res_total = await db.execute(sql_count, (target_date,))
            total_count = res_total[0][0] if res_total else 0

            sql_agg = """
                SELECT 
                    COUNT(*) as count,
                    SUM(CASE WHEN pct_chg > 0 THEN 1 ELSE 0 END) as up_count,
                    SUM(CASE WHEN pct_chg < 0 THEN 1 ELSE 0 END) as down_count,
                    SUM(CASE WHEN pct_chg = 0 THEN 1 ELSE 0 END) as flat_count,
                    SUM(CASE WHEN pct_chg >= 0.05 THEN 1 ELSE 0 END) as up_5pct_count,
                    SUM(CASE WHEN pct_chg <= -0.05 THEN 1 ELSE 0 END) as down_5pct_count,
                    SUM(CASE WHEN pct_chg >= 0.09 THEN 1 ELSE 0 END) as up_9pct_count,
                    SUM(CASE WHEN pct_chg <= -0.09 THEN 1 ELSE 0 END) as down_9pct_count
                FROM stock_kline_daily
                WHERE trade_date = %s
                AND code NOT LIKE '900%%' AND code NOT LIKE '200%%'
            """
            res_agg = await db.execute(sql_agg, (target_date,))
            if not res_agg or not res_agg[0][0]:
                logger.warning(f"当日 {target_date} K线数据不足，无法计算广度")
                return False

            row = res_agg[0]
            curr_count = row[0]
            up_count = row[1]
            down_count = row[2]
            flat_count = row[3]
            up_5pct = row[4]
            down_5pct = row[5]
            up_9pct = row[6]
            down_9pct = row[7]
            
            suspended_count = total_count - curr_count if total_count > curr_count else 0

            # 2. 计算 60 日新高新低
            # 获取第 60 个交易日前的日期
            sql_date_limit = "SELECT DISTINCT trade_date FROM stock_kline_daily WHERE trade_date < %s ORDER BY trade_date DESC LIMIT 59, 1"
            res_limit = await db.execute(sql_date_limit, (target_date,))
            start_date_60 = res_limit[0][0] if res_limit else '1970-01-01'
            
            sql_high_low = """
                SELECT 
                    SUM(CASE WHEN close >= max_60 THEN 1 ELSE 0 END) as h60,
                    SUM(CASE WHEN close <= min_60 THEN 1 ELSE 0 END) as l60
                FROM (
                    SELECT k1.code, k1.close, 
                           (SELECT MAX(k2.close) FROM stock_kline_daily k2 
                            WHERE k2.code = k1.code AND k2.trade_date < k1.trade_date 
                            AND k2.trade_date >= %s) as max_60,
                           (SELECT MIN(k2.close) FROM stock_kline_daily k2 
                            WHERE k2.code = k1.code AND k2.trade_date < k1.trade_date 
                            AND k2.trade_date >= %s) as min_60
                    FROM stock_kline_daily k1
                    WHERE k1.trade_date = %s
                    AND k1.code NOT LIKE '900%%' AND k1.code NOT LIKE '200%%'
                ) t
            """
            res_hl = await db.execute(sql_high_low, (start_date_60, start_date_60, target_date))
            high_60d = res_hl[0][0] if res_hl and res_hl[0][0] is not None else 0
            low_60d = res_hl[0][1] if res_hl and res_hl[0][1] is not None else 0
            
            query = """
                INSERT INTO ods_market_breadth_daily (
                    trade_date, total_count, up_count, down_count, flat_count, 
                    suspended_count, up_5pct_count, down_5pct_count, 
                    up_9pct_count, down_9pct_count, high_60d_count, low_60d_count
                ) VALUES (
                    %s, %s, %s, %s, %s, 
                    %s, %s, %s, 
                    %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                total_count=VALUES(total_count), up_count=VALUES(up_count),
                down_count=VALUES(down_count), flat_count=VALUES(flat_count),
                suspended_count=VALUES(suspended_count), up_5pct_count=VALUES(up_5pct_count),
                down_5pct_count=VALUES(down_5pct_count), up_9pct_count=VALUES(up_9pct_count),
                down_9pct_count=VALUES(down_9pct_count), high_60d_count=VALUES(high_60d_count),
                low_60d_count=VALUES(low_60d_count)
            """
            await db.execute(query, (
                target_date, total_count, up_count, down_count, flat_count,
                suspended_count, up_5pct, down_5pct,
                up_9pct, down_9pct, high_60d, low_60d
            ))
            return True
        except Exception as e:
            logger.error(f"同步市场广度失败: {target_date}, {e}")
            raise

    async def sync_limit_pool(self, target_date: str):
        """从 AkShare 同步涨跌停池到 ods_event_limit_pool"""
        try:
            pools = ['zt', 'dt', 'zb', 'lian']
            total_synced = 0
            
            for pool_type in pools:
                url = f"{self.akshare_url}/api/v1/market/limit_pool"
                params = {"date": target_date, "pool_type": pool_type}
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                
                if not data:
                    continue

                query = """
                    INSERT INTO ods_event_limit_pool (
                        trade_date, ts_code, name, pool_type, close, pct_chg, 
                        amount, circ_mv, turnover_rate, first_limit_time, 
                        last_limit_time, board_height, seal_money, seal_count, 
                        open_times, industry
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, 
                        %s, %s, %s, %s, 
                        %s, %s
                    ) ON DUPLICATE KEY UPDATE
                    name=VALUES(name), close=VALUES(close), pct_chg=VALUES(pct_chg),
                    amount=VALUES(amount), circ_mv=VALUES(circ_mv), 
                    turnover_rate=VALUES(turnover_rate), board_height=VALUES(board_height),
                    seal_money=VALUES(seal_money)
                """
                args = []
                for i in data:
                    # 补齐代码后缀
                    code = i.get("code")
                    if code:
                        if code.startswith('6'): code = f"{code}.SH"
                        elif code.startswith(('0', '3')): code = f"{code}.SZ"
                        elif code.startswith(('8', '4')): code = f"{code}.BJ"
                    
                    args.append((
                        target_date, code, i.get("name"), pool_type, i.get("close"), i.get("pct_chg"),
                        i.get("amount"), i.get("circ_mv"), i.get("turnover_rate"), i.get("first_limit_time"),
                        i.get("last_limit_time"), i.get("board_height"), i.get("seal_money"), i.get("seal_count"),
                        i.get("open_times"), i.get("industry")
                    ))
                
                await db.execute_many(query, args)
                total_synced += len(args)
                logger.info(f"同步涨跌停池 [{pool_type}]: {len(args)} 条")
                
            return total_synced
        except Exception as e:
            logger.error(f"同步涨跌停池失败: {target_date}, {e}")
            raise
