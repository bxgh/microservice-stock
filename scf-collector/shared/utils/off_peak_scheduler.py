# -*- coding: utf-8 -*-
"""
[E15-M6-T1] 北京时区安全的错峰分析调度器 off_peak_scheduler.py
提供时区安全的 is_off_peak 检测和精准秒级时差休眠等待。
"""

import pytz
import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

class OffPeakScheduler:
    TZ = pytz.timezone('Asia/Shanghai')

    @classmethod
    def get_beijing_now(cls) -> datetime.datetime:
        """
        获取当前北京时间的 timezone-aware datetime 对象
        """
        return datetime.datetime.now(cls.TZ)

    @classmethod
    def is_off_peak(cls, dt: datetime.datetime = None) -> bool:
        """
        检查指定（或当前）时间是否属于北京时间错峰优惠时段 (00:30 - 08:30)
        """
        if dt is None:
            dt = cls.get_beijing_now()
        else:
            # 如果 dt 是 naive datetime，则强制本地化到 Asia/Shanghai
            if dt.tzinfo is None:
                dt = cls.TZ.localize(dt)
            else:
                dt = dt.astimezone(cls.TZ)
        
        time_now = dt.time()
        start = datetime.time(0, 30)
        end = datetime.time(8, 30)
        return start <= time_now <= end

    @classmethod
    async def wait_for_off_peak(cls):
        """
        休眠并静默等候，直至进入下一个北京时间 00:30-08:30 优惠时段。
        如果当前已经处于优惠时段，则立即返回，不做休眠。
        """
        now = cls.get_beijing_now()
        if cls.is_off_peak(now):
            logger.info("Currently in off-peak hours (00:30-08:30 Beijing time). Executing immediately.")
            return

        seconds_to_wait = calculate_wait_seconds(now)
        target = now + datetime.timedelta(seconds=seconds_to_wait)
        logger.info(
            f"Currently in peak hours. Sleeping for {seconds_to_wait:.1f} seconds "
            f"(approx {seconds_to_wait / 3600:.2f} hours) until off-peak hour starts at {target} (Beijing time)..."
        )
        await asyncio.sleep(seconds_to_wait)
        logger.info("Woke up from off-peak sleep. Safe to execute tasks now.")


# ==========================================
# 模块级便捷调用接口 (Module-level Wrapper APIs)
# ==========================================

def is_off_peak(dt: datetime.datetime = None) -> bool:
    """检查指定或当前时间是否属于北京时间错峰优惠时段 (00:30 - 08:30)"""
    return OffPeakScheduler.is_off_peak(dt)


async def wait_for_off_peak():
    """休眠挂起直至进入错峰优惠时段"""
    await OffPeakScheduler.wait_for_off_peak()


def calculate_wait_seconds(dt: datetime.datetime = None) -> float:
    """计算指定（或当前）时间距离下一次错峰低能耗时段（北京时间 00:30）的秒数"""
    if dt is None:
        dt = OffPeakScheduler.get_beijing_now()
    else:
        if dt.tzinfo is None:
            dt = OffPeakScheduler.TZ.localize(dt)
        else:
            dt = dt.astimezone(OffPeakScheduler.TZ)

    target = dt.replace(hour=0, minute=30, second=0, microsecond=0)
    if dt.time() > datetime.time(8, 30):
        target += datetime.timedelta(days=1)
    else:
        if dt > target:
            target += datetime.timedelta(days=1)

    return (target - dt).total_seconds()

