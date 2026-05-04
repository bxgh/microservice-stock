import datetime
from typing import Dict, Any, List
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("stock-manager.calendar")

class CalendarService:
    """交易日历服务"""
    
    async def get_trading_days(self, week: str = "current") -> Dict[str, Any]:
        """获取交易状态日历"""
        if week == "current":
            today = datetime.date.today()
            start_date = today - datetime.timedelta(days=today.weekday())
            week_label = today.strftime("%Y-W%V")
        else:
            try:
                year_part, week_part = week.split("-W")
                start_date = datetime.datetime.strptime(f"{year_part}-W{week_part}-1", "%G-W%V-%u").date()
                week_label = week
            except Exception as e:
                logger.error(f"解析周格式失败: {e}")
                raise ValueError("Invalid week format. Use 'current' or 'YYYY-Www'")
        
        end_date = start_date + datetime.timedelta(days=6)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        sql = "SELECT cal_date, is_open FROM trade_cal WHERE cal_date BETWEEN %s AND %s"
        rows = await db.execute(sql, (start_str, end_str))
        
        trading_days = []
        holidays = []
        holiday_names = {"01-01": "元旦", "10-01": "国庆节", "05-01": "劳动节", "02-14": "情人节"}
        
        for row in rows:
            d = row[0]
            is_open = int(row[1])
            is_trading_day = (is_open == 1)
            
            day_item = {
                "date": d.strftime("%Y-%m-%d"),
                "dayOfWeek": d.weekday() + 1,
                "isHoliday": not is_trading_day
            }
            
            if d.weekday() < 5:
                trading_days.append(day_item)
            
            if not is_trading_day and d.weekday() < 5:
                m_d = d.strftime("%m-%d")
                holidays.append({
                    "date": d.strftime("%Y-%m-%d"),
                    "name": holiday_names.get(m_d, "休市")
                })
        
        return {
            "weekLabel": week_label,
            "tradingDays": trading_days,
            "holidays": holidays
        }

    async def is_trading_day(self, date_str: str = None) -> bool:
        """检查指定日期是否为交易日"""
        if not date_str:
            date_str = datetime.date.today().strftime("%Y-%m-%d")
            
        sql = "SELECT is_open FROM trade_cal WHERE cal_date = %s"
        res = await db.execute(sql, (date_str,))
        if res and int(res[0][0]) == 1:
            return True
        return False
