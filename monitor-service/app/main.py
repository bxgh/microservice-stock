from fastapi import FastAPI, BackgroundTasks
from app.services.syncer import syncer
from app.services.calculators import monitor_engine
from app.utils.database import db
from app.utils.logger import setup_logger, get_logger

# 初始化全局日志
setup_logger("monitor-service")
logger = get_logger("monitor-service.main")

app = FastAPI(title="Monitor Service API", version="1.0.0")

@app.on_event("startup")
async def startup():
    await db.connect()
    logger.info("Monitor Service 已启动，数据库连接池已就绪")

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()
    logger.info("Monitor Service 已关闭")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/v1/sync/daily")
async def sync_daily(background_tasks: BackgroundTasks, date: str = None):
    """异步执行每日数据同步任务"""
    background_tasks.add_task(syncer.sync_lhb_daily, date)
    background_tasks.add_task(syncer.sync_block_trade_daily, date)
    background_tasks.add_task(syncer.sync_margin_summary)
    background_tasks.add_task(syncer.sync_market_stats)
    return {"status": "accepted", "message": "数据同步任务已加入后台队列"}

@app.post("/api/v1/calculate")
async def calculate(background_tasks: BackgroundTasks, date: str = None):
    """异步执行监控指标计算"""
    if date:
        background_tasks.add_task(monitor_engine.run_daily_calculation, date)
    else:
        # 默认计算逻辑可通过定时任务调用
        pass
    return {"status": "accepted", "message": f"计算任务 ({date or 'latest'}) 已加入后台队列"}
