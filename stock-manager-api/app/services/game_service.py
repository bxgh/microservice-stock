from typing import Dict, Any, List, Optional
from datetime import datetime
from app.utils.database import db
from app.utils.http_client import http_client
from app.utils.logger import get_logger

logger = get_logger("stock-manager.game")


class GameService:
    """博弈维度数据同步服务"""

    async def fetch_lhb_daily(self, date: str) -> List[Dict[str, Any]]:
        """从 akshare-api 获取龙虎榜全榜"""
        try:
            path = "/api/v1/dragon_tiger/daily"
            params = {"date": date}
            data = await http_client.get("akshare", path, params=params)
            return data
        except Exception as e:
            logger.error(f"fetch_lhb_daily failed: date={date}, error={e}")
            raise

    async def fetch_lhb_institution(self, date: str) -> List[Dict[str, Any]]:
        """从 akshare-api 获取龙虎榜机构统计"""
        try:
            path = "/api/v1/dragon_tiger/institution"
            params = {"date": date}
            data = await http_client.get("akshare", path, params=params)
            return data
        except Exception as e:
            logger.error(
                f"fetch_lhb_institution failed: date={date}, error={e}")
            raise

    async def fetch_north_funds(self, date: str) -> List[Dict[str, Any]]:
        """从 akshare-api 获取北向资金持股"""
        try:
            path = "/api/v1/north/daily"
            params = {"date": date}
            data = await http_client.get("akshare", path, params=params)
            return data
        except Exception as e:
            logger.error(f"fetch_north_funds failed: date={date}, error={e}")
            raise

    async def sync_lhb_daily(self, date: str) -> int:
        """同步龙虎榜每日汇总 (合并 Detail 和 Institution)"""
        # 1. 获取全榜
        lhb_list = await self.fetch_lhb_daily(date)
        if not lhb_list:
            return 0

        # 2. 获取机构榜 (可能为空)
        inst_list = []
        try:
            inst_list = await self.fetch_lhb_institution(date)
        except Exception:
            pass  # 允许机构榜失败，不影响全榜入库

        # 建立机构数据索引 (code -> dict)
        inst_map = {item["code"]: item for item in inst_list}

        sql = """
            INSERT INTO stock_lhb_daily
            (ts_code, trade_date, close_price, change_pct, turnover_rate,
             net_buy_amt, turnover_amt, reason,
             inst_net_buy_amt, inst_buy_amt, inst_sell_amt, inst_buy_count, inst_sell_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                close_price = VALUES(close_price),
                change_pct = VALUES(change_pct),
                turnover_rate = VALUES(turnover_rate),
                net_buy_amt = VALUES(net_buy_amt),
                turnover_amt = VALUES(turnover_amt),
                reason = VALUES(reason),
                inst_net_buy_amt = VALUES(inst_net_buy_amt),
                inst_buy_amt = VALUES(inst_buy_amt),
                inst_sell_amt = VALUES(inst_sell_amt),
                inst_buy_count = VALUES(inst_buy_count),
                inst_sell_count = VALUES(inst_sell_count),
                updated_at = CURRENT_TIMESTAMP
        """

        rows = []
        for item in lhb_list:
            code = item.get("code")
            if not code:
                continue

            # 整合机构数据
            inst_data = inst_map.get(code, {})

            rows.append((
                code,
                date,  # 使用传入的date确保一致
                item.get("close"),
                item.get("change_pct"),
                item.get("turnover_rate"),
                item.get("net_buy"),
                item.get("turnover"),  # detail 接口通常不返回成交额? check response
                item.get("reason"),

                inst_data.get("inst_net_buy_amt"),
                inst_data.get("inst_buy_amt"),
                inst_data.get("inst_sell_amt"),
                inst_data.get("buy_inst_count"),
                inst_data.get("sell_inst_count")
            ))

        if rows:
            await db.execute_many(sql, rows)
            logger.info(f"LHB sync success: date={date}, count={len(rows)}")
            return len(rows)
        return 0

    async def sync_north_funds_daily(self, date: str) -> int:
        """同步北向资金每日持股"""
        data = await self.fetch_north_funds(date)
        if not data:
            return 0

        sql = """
            INSERT INTO stock_north_funds_daily
            (ts_code, trade_date, hold_count, hold_market_cap, hold_ratio)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                hold_count = VALUES(hold_count),
                hold_market_cap = VALUES(hold_market_cap),
                hold_ratio = VALUES(hold_ratio),
                updated_at = CURRENT_TIMESTAMP
        """

        rows = []
        for item in data:
            code = item.get("code")
            if not code:
                continue

            rows.append((
                code,
                item.get("date"),
                item.get("hold_count"),
                item.get("hold_market_cap"),
                item.get("hold_ratio")
            ))

        if rows:
            await db.execute_many(sql, rows)
            logger.info(
                f"North Funds sync success: date={date}, count={
                    len(rows)}")
            return len(rows)
        return 0

    async def sync_north_funds_history(self, code: str) -> int:
        """同步个股北向资金持股历史 (from 2016-01-01 to now)"""
        start_date = "2016-01-01"  # 深股通 2016开通，沪股通 2014
        end_date = datetime.now().strftime("%Y-%m-%d")

        try:
            path = f"/api/v1/north/history/{code}"
            params = {"start_date": start_date, "end_date": end_date}
            data = await http_client.get("akshare", path, params=params)
        except Exception as e:
            logger.error(f"fetch_north_history failed: code={code}, error={e}")
            return 0

        if not data:
            return 0

        sql = """
            INSERT INTO stock_north_funds_daily
            (ts_code, trade_date, hold_count, hold_market_cap, hold_ratio)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                hold_count = VALUES(hold_count),
                hold_market_cap = VALUES(hold_market_cap),
                hold_ratio = VALUES(hold_ratio),
                updated_at = CURRENT_TIMESTAMP
        """

        rows = []
        for item in data:
            date = item.get("date")
            if not date:
                continue

            rows.append((
                code,
                date,
                item.get("hold_count"),
                item.get("hold_market_cap"),
                item.get("hold_ratio")
            ))

        if rows:
            await db.execute_many(sql, rows)
            logger.info(
                f"North Funds history sync success: code={code}, count={
                    len(rows)}")
            return len(rows)
        return 0
