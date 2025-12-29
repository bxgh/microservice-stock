"""
性能优化脚本：为周统计查询添加专用索引

问题：
- stock_kline_daily 表有 1746 万行
- GROUP BY trade_date + COUNT(DISTINCT code) 需要扫描一周内所有数据
- 现有索引 uk_code_date(code, date) 对单独 date 查询效率不高

解决方案：
添加 trade_date 索引以加速日期范围查询
"""
import asyncio
import time
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("optimize_weekly_query")

async def add_date_indexes():
    """添加日期索引以优化周统计查询"""
    try:
        await db.connect()
        
        # 1. 检查并添加 K线表的 trade_date 索引
        logger.info("检查 stock_kline_daily 表索引...")
        result = await db.execute(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema=DATABASE() AND table_name='stock_kline_daily' "
            "AND index_name='idx_trade_date'"
        )
        
        if result[0][0] == 0:
            logger.info("正在为 stock_kline_daily.trade_date 创建索引...")
            start = time.time()
            await db.execute("CREATE INDEX idx_trade_date ON stock_kline_daily(trade_date)")
            elapsed = time.time() - start
            logger.info(f"✅ K线表索引创建完成，耗时: {elapsed:.2f}秒")
        else:
            logger.info("✅ K线表 trade_date 索引已存在")
        
        # 2. 检查并添加复权因子表的 adjust_date 索引
        logger.info("检查 stock_adjust_factor 表索引...")
        result = await db.execute(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema=DATABASE() AND table_name='stock_adjust_factor' "
            "AND index_name='idx_adjust_date'"
        )
        
        if result[0][0] == 0:
            logger.info("正在为 stock_adjust_factor.adjust_date 创建索引...")
            start = time.time()
            await db.execute("CREATE INDEX idx_adjust_date ON stock_adjust_factor(adjust_date)")
            elapsed = time.time() - start
            logger.info(f"✅ 复权因子表索引创建完成，耗时: {elapsed:.2f}秒")
        else:
            logger.info("✅ 复权因子表 adjust_date 索引已存在")
        
        logger.info("\n🎉 所有索引已就绪！预期查询性能提升 10-100 倍")
        
        await db.disconnect()
        
    except Exception as e:
        logger.error(f"索引创建失败: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(add_date_indexes())
