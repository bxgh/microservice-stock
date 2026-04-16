import asyncio
import logging
import sys
import click
from app.services.syncer import syncer
from app.utils.database import db
from app.services.calculators import monitor_engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("monitor-service.main")

async def run_backfill():
    try:
        await db.connect()
        await syncer.backfill_all()
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
    finally:
        await db.disconnect()

@click.group()
def cli():
    pass

@cli.command()
def backfill():
    """同步所有数据"""
    asyncio.run(run_backfill())

@cli.command()
@click.option('--date', help='Calculate for specific date (YYYY-MM-DD)')
def calculate(date):
    """计算监控指标"""
    async def run():
        await db.connect()
        if date:
            await monitor_engine.run_daily_calculation(date)
        else:
            # 获取数据库中缺失计算的交易日并按顺序计算 (增量模式)
            query = """
                SELECT DISTINCT t1.trade_date 
                FROM raw_sector_daily t1 
                LEFT JOIN monitor_health_scores t2 ON t1.trade_date = t2.trade_date 
                WHERE t2.trade_date IS NULL 
                ORDER BY t1.trade_date ASC
            """
            rows = await db.execute(query)
            for r in rows:
                dt = r[0].strftime("%Y-%m-%d") if hasattr(r[0], 'strftime') else str(r[0])
                try:
                    logger.info(f"正在计算日期: {dt}")
                    await monitor_engine.run_daily_calculation(dt)
                except Exception as e:
                    logger.error(f"计算失败 {dt}: {e}")
        await db.disconnect()
    
    asyncio.run(run())

if __name__ == "__main__":
    cli()
