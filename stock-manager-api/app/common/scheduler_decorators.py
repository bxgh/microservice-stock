import logging
import asyncio
from functools import wraps
from datetime import date
from typing import Callable, Any

logger = logging.getLogger("stock-manager.scheduler")

def trading_day_only(check_next: bool = False):
    """
    交易日过滤器装饰器
    
    Args:
        check_next: 为 True 时校验下一交易日 (适用于盘前任务), 
                   为 False 时校验当日 (适用于收盘后任务).
    """
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                from app.services.calendar_service import CalendarService
                service = CalendarService()
                
                today = date.today()
                
                if check_next:
                    # 盘前任务：检查从今天开始算的下一个交易日是否是今天或以后
                    # 简单起见，目前业务主要关注“今天是否运行”，
                    # 如果需要更精确的 check_next (例如周末凌晨跑周一的任务), 
                    # 需要 get_next_trading_day 接口。
                    # 这里保持与方案逻辑一致。
                    target_date = today # 占位逻辑，后续可扩展
                else:
                    target_date = today
                
                is_trading = await service.is_trading_day(target_date)
                
                if not is_trading:
                    logger.info(f"【任务拦截】[{func.__name__}] 跳过: {target_date} 为非交易日")
                    return {"status": "skipped", "reason": "non_trading_day", "date": target_date.isoformat()}
                
                return await func(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"【装饰器异常】校验交易日失败: {e}")
                # 降级：异常时允许执行，确保系统不因日历服务挂掉而瘫痪
                return await func(*args, **kwargs)
                
        return wrapper
    return decorator
