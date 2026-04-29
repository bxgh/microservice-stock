import datetime
from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("gateway.calendar_service")

class CalendarService:
    """交易日历服务"""

    async def get_trading_days(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[str]:
        """获取指定范围内的所有交易日 (is_open=1)"""
        try:
            if not start_date:
                # 默认获取最近30天
                today = datetime.date.today()
                start_date = (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
            
            if not end_date:
                # 默认到今天
                end_date = datetime.date.today().strftime("%Y-%m-%d")

            sql = "SELECT cal_date FROM trade_cal WHERE cal_date BETWEEN %s AND %s AND is_open = 1 ORDER BY cal_date ASC"
            rows = await db.execute(sql, (start_date, end_date))
            
            # rows 返回的是字典列表，使用键名访问
            return [row["cal_date"].strftime("%Y-%m-%d") if isinstance(row["cal_date"], (datetime.date, datetime.datetime)) else str(row["cal_date"]) for row in rows]
        except Exception as e:
            logger.error(f"获取交易日列表失败: {e}")
            return None

    async def is_trading_day(self, check_date: Optional[str] = None) -> Dict[str, Any]:
        """检查特定日期是否为交易日"""
        try:
            if not check_date:
                check_date = datetime.date.today().strftime("%Y-%m-%d")
            
            sql = "SELECT is_open FROM trade_cal WHERE cal_date = %s"
            rows = await db.execute(sql, (check_date,))
            
            if not rows:
                return {"date": check_date, "is_open": False, "status": "unknown"}
            
            is_open = int(rows[0]["is_open"]) == 1
            return {
                "date": check_date,
                "is_open": is_open,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"检查交易日状态失败: {e}")
            return None

    async def get_recent_trading_days(self, limit: int = 5) -> List[str]:
        """获取最近的 N 个交易日"""
        try:
            sql = "SELECT cal_date FROM trade_cal WHERE is_open = 1 AND cal_date <= %s ORDER BY cal_date DESC LIMIT %s"
            today = datetime.date.today().strftime("%Y-%m-%d")
            rows = await db.execute(sql, (today, limit))
            
            days = [row["cal_date"].strftime("%Y-%m-%d") if isinstance(row["cal_date"], (datetime.date, datetime.datetime)) else str(row["cal_date"]) for row in rows]
            return sorted(days)
        except Exception as e:
            logger.error(f"获取最近交易日失败: {e}")
            return None

calendar_service = CalendarService()
