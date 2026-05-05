import zlib
import datetime
from typing import List, Set
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("stock-manager.sampling")


class SamplingService:
    """分层抽样服务 (E4)"""

    async def get_hs300_members(self) -> Set[str]:
        """获取沪深300成分股清单"""
        try:
            # 优先从同花顺成分表获取
            sql = """
                SELECT DISTINCT c.ts_code FROM stock_sector_cons_ths c
                JOIN stock_sector_ths s ON c.sector_id = s.id
                WHERE s.sector_name LIKE '%沪深300%'
            """
            rows = await db.execute(sql)
            if not rows:
                logger.warning("未能在数据库中找到沪深300成分股记录")
                return set()
            return {row[0] for row in rows}
        except Exception as e:
            logger.error(f"获取沪深300成分股失败: {e}")
            return set()

    async def get_all_active_stocks(self) -> List[str]:
        """获取全市场在运行股票清单"""
        try:
            # list_status = 'L' 表示上市状态
            sql = "SELECT ts_code FROM stock_basic_info WHERE list_status = 'L'"
            rows = await db.execute(sql)
            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"获取全市场股票失败: {e}")
            return []

    async def get_daily_inspection_list(
            self, target_date: datetime.date = None) -> List[str]:
        """
        生成当日巡检清单:
        1. 核心桶: 沪深300 (100% 覆盖)
        2. 轮转桶: 1/7 滚动覆盖全市场
        """
        if not target_date:
            target_date = datetime.date.today()

        # 1. 核心桶
        core_set = await self.get_hs300_members()

        # 2. 轮转桶 (1/7)
        all_stocks = await self.get_all_active_stocks()
        # 使用星期几作为种子 (0-6)
        day_index = target_date.weekday()

        rolling_list = []
        for code in all_stocks:
            if code in core_set:
                continue
            # 稳定哈希分片
            if zlib.crc32(code.encode()) % 7 == day_index:
                rolling_list.append(code)

        final_list = list(core_set) + rolling_list
        logger.info(
            f"生成巡检清单: 日期={target_date}, 总数={
                len(final_list)} (核心={
                len(core_set)}, 轮转={
                len(rolling_list)})")

        return final_list


sampling_service = SamplingService()
