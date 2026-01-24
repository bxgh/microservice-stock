from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.utils.database import db
from app.utils.http_client import http_client
from app.utils.logger import get_logger

logger = get_logger("stock-manager.chips")

class ChipService:
    """筹码维度数据同步服务"""
    
    async def fetch_restricted_release(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """从 akshare-api 获取限售解禁数据"""
        try:
            path = "/api/v1/restricted/release"
            params = {"start_date": start_date, "end_date": end_date}
            data = await http_client.get("akshare", path, params=params)
            return data
        except Exception as e:
            logger.error(f"从 akshare-api 获取限售解禁失败: start={start_date}, end={end_date}, error={e}")
            raise

    async def fetch_block_trade_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """从 akshare-api 获取大宗交易数据 (日期范围)"""
        try:
            path = "/api/v1/block_trade/daily"
            params = {"start_date": start_date, "end_date": end_date}
            data = await http_client.get("akshare", path, params=params)
            return data
        except Exception as e:
            logger.error(f"从 akshare-api 获取大宗交易失败: start={start_date}, end={end_date}, error={e}")
            raise

    async def sync_restricted_release(self, start_date: str, end_date: str) -> int:
        """同步限售解禁数据"""
        data = await self.fetch_restricted_release(start_date, end_date)
        if not data:
            return 0
        
        sql = """
            INSERT INTO stock_restricted_release 
            (ts_code, release_date, release_count, release_market_cap, ratio, holder_type)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                release_count = VALUES(release_count),
                release_market_cap = VALUES(release_market_cap),
                ratio = VALUES(ratio),
                holder_type = VALUES(holder_type),
                updated_at = CURRENT_TIMESTAMP
        """
        
        rows = []
        for item in data:
            code = item.get("code", "")
            if not code: continue
            
            rows.append((
                code,
                item.get("release_date"),
                item.get("release_count"),
                item.get("release_market_cap"),
                item.get("ratio"),
                item.get("holder_type")
            ))
            
        if rows:
            await db.execute_many(sql, rows)
            logger.info(f"限售解禁同步成功: {start_date} to {end_date}, count={len(rows)}")
            return len(rows)
        return 0

    async def sync_block_trade_range(self, start_date: str, end_date: str) -> int:
        """同步日期范围内的大宗交易数据"""
        data = await self.fetch_block_trade_range(start_date, end_date)
        if not data:
            return 0
            
        # Clear existing data for that range to avoid double counting
        clear_sql = "DELETE FROM stock_block_trade WHERE trade_date BETWEEN %s AND %s"
        await db.execute(clear_sql, (start_date, end_date))
        
        sql = """
            INSERT INTO stock_block_trade 
            (ts_code, trade_date, price, volume, amount, buyer, seller)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        rows = []
        for item in data:
            code = item.get("code", "")
            if not code: continue
            
            rows.append((
                code,
                item.get("date"),
                item.get("price"),
                item.get("volume"),
                item.get("amount"),
                item.get("buyer"),
                item.get("seller")
            ))
            
        if rows:
            await db.execute_many(sql, rows)
            logger.info(f"大宗交易范围同步成功: {start_date} to {end_date}, count={len(rows)}")
            return len(rows)
        return 0

    async def sync_block_trade(self, date: str) -> int:
        """同步某日大宗交易数据"""
        return await self.sync_block_trade_range(date, date)
