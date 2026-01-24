from typing import List, Dict, Any, Optional
from datetime import datetime
from app.utils.database import db
from app.utils.http_client import http_client
from app.utils.logger import get_logger

logger = get_logger("stock-manager.information")

class InformationService:
    """信息维度数据服务"""

    # -------------------------------------------------------------------------
    # 1. 机构评级 (Analyst Rank)
    # -------------------------------------------------------------------------
    async def sync_analyst_ranks(self, data: List[Dict[str, Any]]) -> int:
        if not data:
            return 0
        
        sql = """
            INSERT INTO stock_analyst_rank
            (stock_code, report_date, analyst, rating, change_direction, target_price)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                rating = VALUES(rating),
                change_direction = VALUES(change_direction),
                target_price = VALUES(target_price),
                created_at = CURRENT_TIMESTAMP
        """
        
        rows = []
        for item in data:
            rows.append((
                item.get("stock_code"),
                item.get("report_date"),
                item.get("analyst"),
                item.get("rating"),
                item.get("change_direction"),
                item.get("target_price")
            ))
            
        try:
            await db.execute_many(sql, rows)
            logger.info(f"同步机构评级成功: count={len(rows)}")
            return len(rows)
        except Exception as e:
            logger.error(f"同步机构评级失败: {e}")
            raise

    async def get_analyst_ranks(self, code: str, limit: int = 50) -> List[Dict[str, Any]]:
        sql = """
            SELECT id, stock_code, report_date, analyst, rating, change_direction, target_price, created_at
            FROM stock_analyst_rank
            WHERE stock_code = %s
            ORDER BY report_date DESC
            LIMIT %s
        """
        rows = await db.execute(sql, (code, limit))
        return [
            {
                "id": r[0], "stock_code": r[1], "report_date": r[2], "analyst": r[3],
                "rating": r[4], "change_direction": r[5], "target_price": float(r[6]) if r[6] else None,
                "created_at": r[7]
            } for r in rows
        ]

    # -------------------------------------------------------------------------
    # 2. 业绩预告 (Performance Forecast)
    # -------------------------------------------------------------------------
    async def sync_forecasts(self, data: List[Dict[str, Any]]) -> int:
        if not data:
            return 0
            
        sql = """
            INSERT INTO stock_performance_forecast
            (stock_code, notice_date, report_period, type, growth_min, growth_max)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                notice_date = VALUES(notice_date),
                type = VALUES(type),
                growth_min = VALUES(growth_min),
                growth_max = VALUES(growth_max)
        """
        
        rows = []
        for item in data:
            rows.append((
                item.get("stock_code"),
                item.get("notice_date"),
                item.get("report_period"),
                item.get("type"),
                item.get("growth_min"),
                item.get("growth_max")
            ))
            
        try:
            await db.execute_many(sql, rows)
            logger.info(f"同步业绩预告成功: count={len(rows)}")
            return len(rows)
        except Exception as e:
            logger.error(f"同步业绩预告失败: {e}")
            raise

    async def get_forecasts(self, code: str, limit: int = 20) -> List[Dict[str, Any]]:
        sql = """
            SELECT id, stock_code, notice_date, report_period, type, growth_min, growth_max
            FROM stock_performance_forecast
            WHERE stock_code = %s
            ORDER BY report_period DESC
            LIMIT %s
        """
        rows = await db.execute(sql, (code, limit))
        return [
            {
                "id": r[0], "stock_code": r[1], "notice_date": r[2], "report_period": r[3],
                "type": r[4], "growth_min": float(r[5]) if r[5] else None, "growth_max": float(r[6]) if r[6] else None
            } for r in rows
        ]

    # -------------------------------------------------------------------------
    # 3. 市场热度 (Sentiment Daily)
    # -------------------------------------------------------------------------
    async def sync_sentiment(self, data: List[Dict[str, Any]]) -> int:
        if not data:
            return 0
            
        sql = """
            INSERT INTO stock_sentiment_daily
            (stock_code, trade_date, post_count, read_count, comment_count, rank_score)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                post_count = VALUES(post_count),
                read_count = VALUES(read_count),
                comment_count = VALUES(comment_count),
                rank_score = VALUES(rank_score)
        """
        
        rows = []
        for item in data:
            rows.append((
                item.get("stock_code"),
                item.get("trade_date"),
                item.get("post_count", 0),
                item.get("read_count", 0),
                item.get("comment_count", 0),
                item.get("rank_score", 0)
            ))
            
        try:
            await db.execute_many(sql, rows)
            logger.info(f"同步市场热度成功: count={len(rows)}")
            return len(rows)
        except Exception as e:
            logger.error(f"同步市场热度失败: {e}")
            raise

    async def get_sentiment(self, code: str, limit: int = 30) -> List[Dict[str, Any]]:
        sql = """
            SELECT id, stock_code, trade_date, post_count, read_count, comment_count, rank_score
            FROM stock_sentiment_daily
            WHERE stock_code = %s
            ORDER BY trade_date DESC
            LIMIT %s
        """
        rows = await db.execute(sql, (code, limit))
        return [
            {
                "id": r[0], "stock_code": r[1], "trade_date": r[2],
                "post_count": r[3], "read_count": r[4], "comment_count": r[5], "rank_score": r[6]
            } for r in rows
        ]

    # -------------------------------------------------------------------------
    # Orchestration Methods (Fetch from AkShare API -> Save to DB)
    # -------------------------------------------------------------------------
    
    async def sync_analyst_ranks_from_akshare(self, report_date: Optional[str] = None) -> int:
        """从 AkShare API 获取并同步机构评级"""
        try:
            params = {}
            if report_date:
                params["date"] = report_date
                
            data = await http_client.get("akshare", "/api/v1/information/analyst-ranks", params=params)
            if not data:
                return 0
            
            # 统一洗入 DB 格式
            clean_items = []
            for item in data:
                rpt_date = item.get("report_date")
                if not rpt_date or rpt_date == "":
                    continue
                    
                clean_items.append({
                    "stock_code": item.get("stock_code"),
                    "report_date": rpt_date,
                    "analyst": item.get("analyst"),
                    "rating": item.get("rating"),
                    "change_direction": item.get("change_direction"),
                    "target_price": item.get("target_price")
                })
            
            return await self.sync_analyst_ranks(clean_items)
        except Exception as e:
            logger.error(f"Orchestration sync_analyst_ranks failed: {e}")
            raise

    async def sync_forecasts_from_akshare(self, period: str) -> int:
        """从 AkShare API 获取并同步业绩预告"""
        try:
            params = {"period": period}
            data = await http_client.get("akshare", "/api/v1/information/forecasts", params=params)
            if not data:
                return 0
                
            clean_items = []
            for item in data:
                clean_items.append({
                    "stock_code": item.get("stock_code"),
                    "notice_date": item.get("notice_date"),
                    "report_period": item.get("report_period"),
                    "type": item.get("type"),
                    "growth_min": None, 
                    "growth_max": None
                })
                
            return await self.sync_forecasts(clean_items)
        except Exception as e:
            logger.error(f"Orchestration sync_forecasts failed: {e}")
            raise

    async def sync_sentiment_from_akshare(self, code: str) -> int:
        """从 AkShare API 获取并同步个股今日热度"""
        try:
            data = await http_client.get("akshare", f"/api/v1/information/sentiment/{code}")
            if not data:
                return 0
                
            # 获取当前交易日 (简单处理，暂取今日)
            now = datetime.now()
            trade_date = now.strftime("%Y-%m-%d")
            
            clean_item = {
                "stock_code": code,
                "trade_date": trade_date,
                "post_count": data.get("post_count", 0),
                "read_count": data.get("read_count", 0),
                "comment_count": data.get("comment_count", 0),
                "rank_score": data.get("rank_score", 0)
            }
            
            return await self.sync_sentiment([clean_item])
        except Exception as e:
            logger.error(f"Orchestration sync_sentiment failed: code={code}, {e}")
            raise

