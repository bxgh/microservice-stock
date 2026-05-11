from datetime import date, datetime, time
from typing import List, Optional, Tuple
import chinese_calendar
from enum import Enum

class MarketType(Enum):
    CN = "CN"  # A股
    HK = "HK"  # 港股 (暂未实现)
    US = "US"  # 美股 (暂未实现)

class CalendarService:
    """
    日历服务组件
    负责交易日识别和交易时段判断
    """
    
    def __init__(self):
        # A股交易时段配置 (默认)
        self.trading_sessions = [
            (time(9, 15), time(11, 30)),  # 上午 (含集合竞价)
            (time(13, 0), time(15, 5))    # 下午 (含收盘集合竞价)
        ]
        
        # 特殊休市日 (A股特有，非定假日但休市)
        # 例如：2024-02-09 (除夕)，虽然是工作日，但股市休市
        self.special_market_holidays = {
            date(2024, 2, 9), 
        }
        
    def is_trading_day(self, day: Optional[date] = None, market: MarketType = MarketType.CN) -> bool:
        """
        判断是否为交易日
        
        Args:
            day: 日期 (默认今天)
            market: 市场类型
            
        Returns:
            bool: 是否为交易日
        """
        try:
            if day is None:
                day = date.today()
            elif isinstance(day, str):
                day = datetime.strptime(day, "%Y-%m-%d").date()
            elif isinstance(day, datetime):
                day = day.date()
            elif not isinstance(day, date):
                raise ValueError(f"Invalid date type: {type(day)}. Expected date, datetime or str.")
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error processing date: {e}")
            
        if market == MarketType.CN:
            is_weekend = day.weekday() >= 5
            is_holiday = chinese_calendar.is_holiday(day)
            
            if is_weekend:
                return False
                
            if day in self.special_market_holidays:
                return False
                
            if is_holiday:
                return False
                
            return True
            
        else:
            # 其他市场暂不支持，默认返回工作日
            return day.weekday() < 5

    def is_business_hours(self, current_time: Optional[time] = None) -> bool:
        """
        判断当前时间是否在交易时段内
        """
        try:
            if current_time is None:
                current_time = datetime.now().time()
            elif isinstance(current_time, str):
                try:
                    current_time = datetime.strptime(current_time, "%H:%M:%S").time()
                except:
                    current_time = datetime.strptime(current_time, "%H:%M").time()
            elif isinstance(current_time, datetime):
                current_time = current_time.time()
            elif not isinstance(current_time, time):
                raise ValueError(f"Invalid time type: {type(current_time)}. Expected time, datetime or str.")
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error processing time: {e}")
            
        for start, end in self.trading_sessions:
            if start <= current_time <= end:
                return True
                
        return False

    def get_next_trading_day(self, day: Optional[date] = None) -> date:
        """
        获取下一个交易日
        """
        try:
            if day is None:
                day = date.today()
            elif isinstance(day, str):
                day = datetime.strptime(day, "%Y-%m-%d").date()
            elif isinstance(day, datetime):
                day = day.date()
            elif not isinstance(day, date):
                raise ValueError(f"Invalid date type: {type(day)}. Expected date, datetime or str.")
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error processing date: {e}")
            
        next_day = day
        from datetime import timedelta
        
        while True:
            next_day = next_day + timedelta(days=1)
            if self.is_trading_day(next_day):
                return next_day

    def get_last_trading_day(self, day: Optional[date] = None) -> date:
        """
        获取上一个交易日 (含起始日)
        如果起始日本身是交易日，则返回起始日本身。
        """
        try:
            if day is None:
                day = date.today()
            elif isinstance(day, str):
                day = datetime.strptime(day, "%Y-%m-%d").date()
            elif isinstance(day, datetime):
                day = day.date()
            elif not isinstance(day, date):
                raise ValueError(f"Invalid date type: {type(day)}. Expected date, datetime or str.")
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error processing date: {e}")
            
        check_day = day
        from datetime import timedelta
        
        while True:
            if self.is_trading_day(check_day):
                return check_day
            check_day = check_day - timedelta(days=1)
