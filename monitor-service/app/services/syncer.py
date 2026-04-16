import asyncio
import logging
from datetime import datetime, timedelta
from app.core.config import settings
from app.utils.database import db
from app.services.akshare_client import ak_client

logger = logging.getLogger("monitor-service.syncer")

class MarketDataSyncer:
    def __init__(self):
        pass

    def _format_ts_code(self, code: str) -> str:
        """格式化股票代码为 XXXXXX.SH/SZ"""
        if not code: return code
        code = str(code)
        if "." in code: return code
        if code.startswith('6'): return f"{code}.SH"
        if code.startswith('0') or code.startswith('3'): return f"{code}.SZ"
        if code.startswith('8') or code.startswith('4'): return f"{code}.BJ"
        return code

    async def sync_lhb_daily(self, date: str = None):
        """同步某日龙虎榜数据"""
        try:
            today = date or datetime.now().strftime("%Y-%m-%d")
            data = await ak_client.get_lhb_daily(today)
            if not data:
                logger.info(f"龙虎榜: {today} 无数据")
                return

            query = """
                INSERT INTO stock_lhb_daily (ts_code, trade_date, close_price, change_pct, turnover_rate, net_buy_amt, reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                close_price=VALUES(close_price), 
                change_pct=VALUES(change_pct), 
                net_buy_amt=VALUES(net_buy_amt)
            """
            args = []
            for i in data:
                args.append((
                    self._format_ts_code(i.get("code")),
                    i.get("date") or today,
                    i.get("close"),
                    i.get("change_pct"),
                    i.get("turnover_rate"),
                    i.get("net_buy"),
                    i.get("reason")
                ))
            await db.execute_many(query, args)
            logger.info(f"成功同步龙虎榜: {today}, {len(args)} 条")
        except Exception as e:
            logger.error(f"同步龙虎榜失败: {today}, {e}")

    async def sync_block_trade_daily(self, date: str = None):
        """同步某日大宗交易数据"""
        try:
            today = date or datetime.now().strftime("%Y-%m-%d")
            data = await ak_client.get_block_trade_daily(today)
            if not data:
                logger.info(f"大宗交易: {today} 无数据")
                return

            query = """
                INSERT INTO stock_block_trade (trade_date, ts_code, price, volume, amount, buyer, seller)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                price=VALUES(price), 
                amount=VALUES(amount)
            """
            args = []
            for i in data:
                args.append((
                    i.get("date") or today,
                    self._format_ts_code(i.get("code")),
                    i.get("price"),
                    i.get("volume"),
                    i.get("amount"),
                    i.get("buyer"),
                    i.get("seller")
                ))
            await db.execute_many(query, args)
            logger.info(f"成功同步大宗交易: {today}, {len(args)} 条")
        except Exception as e:
            logger.error(f"同步大宗交易失败: {today}, {e}")

    async def sync_margin_summary(self):
        """同步两融汇总汇总历史 (由于数据量小, 每次全量更新最近 60 天)"""
        try:
            data = await ak_client.get_margin_summary()
            if not data:
                return

            query = """
                INSERT INTO market_margin_summary (trade_date, margin_buy, margin_balance)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                margin_buy=VALUES(margin_buy),
                margin_balance=VALUES(margin_balance)
            """
            args = []
            for item in data:
                args.append((
                    item.get("date"),
                    item.get("margin_buy"),
                    item.get("margin_balance")
                ))
            await db.execute_many(query, args)
            logger.info(f"成功同步两融汇总: {len(args)} 条")
        except Exception as e:
            logger.error(f"同步两融汇总失败: {e}")

    async def sync_market_stats(self):
        """同步今日大盘统计数据"""
        try:
            data = await ak_client.get_market_breadth()
            if not data:
                return
            
            # 实时数据仅存今日(或最近交易日)
            # 这里我们假定调用时是交易日收盘后
            today = datetime.now().strftime("%Y-%m-%d")
            
            query = """
                INSERT INTO raw_market_stats 
                (trade_date, advance_count, decline_count, total_market_cap, avg_turnover)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                advance_count=VALUES(advance_count),
                decline_count=VALUES(decline_count),
                total_market_cap=VALUES(total_market_cap),
                avg_turnover=VALUES(avg_turnover)
            """
            await db.execute(query, (
                today, 
                data.get("advance"), 
                data.get("decline"), 
                data.get("total_market_cap"),
                data.get("avg_turnover")
            ))
            logger.info(f"成功同步大盘统计数据: {today}")
        except Exception as e:
            logger.error(f"同步大盘统计失败: {e}")

    async def sync_north_flow(self):
        """同步北向资金汇总历史"""
        try:
            data = await ak_client.get_north_flow_summary()
            if not data:
                return
            
            args = []
            for item in data:
                # 原始日期格式可能是 "2024-04-14"
                args.append((item.get("date"), item.get("north_net_inflow")))
            
            query = """
                INSERT INTO raw_capital_flow_summary (trade_date, north_net_inflow)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE north_net_inflow=VALUES(north_net_inflow)
            """
            await db.execute_many(query, args)
            logger.info(f"成功同步北向资金汇总: {len(args)} 条")
        except Exception as e:
            logger.error(f"同步北向资金流失败: {e}")

    async def sync_sector_daily(self, symbol: str, is_sw=True, years=10):
        """同步行业或 ETF 日线历史"""
        try:
            start_date = (datetime.now() - timedelta(days=years*365)).strftime("%Y%m%d")
            
            if is_sw:
                data = await ak_client.get_sw_index_daily(symbol)
            else:
                data = await ak_client.get_etf_daily(symbol, start_date=start_date)
            
            if not data:
                return
            
            args = []
            for item in data:
                args.append((
                    symbol,
                    item.get("date"),
                    item.get("open"),
                    item.get("high"),
                    item.get("low"),
                    item.get("close"),
                    item.get("volume"),
                    item.get("amount")
                ))
            
            query = """
                INSERT INTO raw_sector_daily 
                (ts_code, trade_date, open, high, low, close, volume, amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                open=VALUES(open), high=VALUES(high), low=VALUES(low),
                close=VALUES(close), volume=VALUES(volume), amount=VALUES(amount)
            """
            await db.execute_many(query, args)
            logger.info(f"成功同步代码 {symbol} 日线: {len(args)} 条")
        except Exception as e:
            logger.error(f"同步日线失败: symbol={symbol}, error={e}")

    async def sync_us_index(self, symbol: str = ".NDX"):
        """同步美股指数历史"""
        try:
            data = await ak_client.get_us_index_daily(symbol)
            if not data:
                return
            
            args = []
            for item in data:
                args.append((
                    symbol,
                    item.get("date"),
                    item.get("open"),
                    item.get("high"),
                    item.get("low"),
                    item.get("close"),
                    item.get("volume"),
                    0 # amount 为 0
                ))
            
            query = """
                INSERT INTO raw_sector_daily 
                (ts_code, trade_date, open, high, low, close, volume, amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                open=VALUES(open), high=VALUES(high), low=VALUES(low),
                close=VALUES(close), volume=VALUES(volume)
            """
            await db.execute_many(query, args)
            logger.info(f"成功同步美股指数 {symbol}: {len(args)} 条")
        except Exception as e:
            logger.error(f"同步美股指数失败: {e}")

    async def backfill_all(self):
        """全量补填 10 年数据"""
        logger.info("启动全量 10 年历史数据补填...")
        
        # 1. 北向资金
        await self.sync_north_flow()
        
        # 2. 申万一级行业 (获取列表并同步)
        # 暂时手工指定核心行业或通过接口动态获取
        sw_indices = ["801010", "801020", "801030", "801040", "801050", "801080", "801110", 
                      "801120", "801130", "801150", "801160", "801170", "801180", "801200", 
                      "801210", "801230", "801710", "801720", "801730", "801740", "801750", 
                      "801760", "801770", "801780", "801790", "801880", "801890", "801950", 
                      "801960", "801970", "801980"]
        
        for code in sw_indices:
            await self.sync_sector_daily(code, is_sw=True, years=10)
            await asyncio.sleep(1) # 避免频率限制
            
        # 3. ETF 篮子
        for code in settings.GROWTH_ETFS + settings.VALUE_ETFS:
            await self.sync_sector_daily(code, is_sw=False, years=10)
            await asyncio.sleep(1)

        # 4. 指数篮子 (CSI 300, 1000)
        # 由于 index_zh_a_hist 需要对应 symbol, 这里暂时复用 sync_sector_daily 逻辑但需调整接口名
        # 为了简化, 我们直接在 akshare_service 中增加对指数的支持
        for code in settings.INDEX_LIST:
            # 这里需要一个新的 sync 逻辑或者让 get_etf_daily/get_index_daily 兼容
            # 我们直接在 ak_client 中调用 get_index_daily
            try:
                start_date = (datetime.now() - timedelta(days=10*365)).strftime("%Y%m%d")
                data = await ak_client.get_index_daily(code, start_date=start_date)
                args = []
                for item in data:
                    args.append((code, item.get("date"), item.get("open"), item.get("high"), item.get("low"), item.get("close"), item.get("volume"), item.get("amount")))
                query = "INSERT INTO raw_sector_daily (ts_code, trade_date, open, high, low, close, volume, amount) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE close=VALUES(close)"
                await db.execute_many(query, args)
                logger.info(f"成功同步指数 {code}: {len(args)} 条")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"同步指数 {code} 失败: {e}")

        # 5. 美股指数
        await self.sync_us_index(".NDX")
        
        logger.info("全量历史数据补填完成。")

syncer = MarketDataSyncer()
