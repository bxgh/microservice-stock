import logging
from ..db.dao import StockDAO

logger = logging.getLogger(__name__)

class TradingDayGuard:
    """
    [E7-S5-T2] 交易日准入拦截器
    负责在任务启动前校验当日是否为交易日，并根据白名单决定是否跳过。
    """

    # 操作白名单：不受交易日限制的操作
    WHITELIST_OPS = [
        'sync_calendar', 
        'verify', 
        'migrate'
    ]

    @staticmethod
    async def should_skip(op: str, biz_date: str) -> bool:
        """
        判断当前操作是否应该跳过
        :param op: 操作码
        :param biz_date: 业务日期 (YYYY-MM-DD)
        :return: True 代表应跳过，False 代表可继续
        """
        if op in TradingDayGuard.WHITELIST_OPS:
            logger.info(f"[TradingDayGuard] Op '{op}' is in whitelist. Bypassing check.")
            return False

        is_trading = await StockDAO.is_trading_day(biz_date)
        if not is_trading:
            logger.warning(f"[TradingDayGuard] {biz_date} is NOT a trading day. Skipping op: {op}")
            return True
        
        logger.info(f"[TradingDayGuard] {biz_date} is a trading day. Proceeding with {op}.")
        return False
