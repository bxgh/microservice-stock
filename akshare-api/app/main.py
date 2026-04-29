import uuid
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from app.api import finance, market, scheduler_api, information
from app.utils.logger import setup_logger
from app.services.akshare_service import AkShareService
from app.scheduler import TaskScheduler, set_scheduler_instance

# 初始化日志
logger = setup_logger("akshare-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("AkShare API 服务启动")
    
    # 1. 初始化 Service
    app.state.akshare_service = AkShareService()
    
    # 0. 初始化数据库
    from app.utils.database import db
    try:
        await db.connect()
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
    
    # 2. 初始化并启动调度器
    scheduler = TaskScheduler()
    set_scheduler_instance(scheduler)
    
    # 注册一个心跳任务（演示用，确保 UI 能看到任务）
    async def heartbeat():
        logger.debug("AkShare 调度器心跳存活")
    
    scheduler.add_interval_job(heartbeat, "akshare_heartbeat", seconds=3600)
    
    # 注册每日ETF同步任务 (17:30)
    from app.scheduler import jobs as job_funcs
    scheduler.add_daily_job(
        job_funcs.daily_etf_kline_sync_job,
        hour=17,
        minute=30,
        job_id="daily_etf_kline_sync"
    )

    # 注册每周元数据同步任务 (周六 02:00)
    scheduler.add_cron_job(
        job_funcs.weekly_metadata_sync_job,
        hour=2,
        minute=0,
        day_of_week=5,
        job_id="weekly_metadata_sync"
    )

    # 注册每日市场数据同步 (19:00)
    scheduler.add_daily_job(
        job_funcs.daily_market_data_sync_job,
        hour=19,
        minute=0,
        job_id="daily_market_data_sync"
    )

    # 注册每日 L2 结构分化数据同步 (19:15)
    scheduler.add_daily_job(
        job_funcs.daily_l2_structural_sync_job,
        hour=19,
        minute=15,
        job_id="daily_l2_structural_sync"
    )

    # 注册每日情绪数据同步 (19:45)
    scheduler.add_daily_job(
        job_funcs.daily_sentiment_sync_job,
        hour=19,
        minute=45,
        job_id="daily_sentiment_sync"
    )

    # 注册每周股票列表同步 (周六 01:00)
    scheduler.add_cron_job(
        job_funcs.weekly_stock_list_sync_job,
        hour=1,
        minute=0,
        day_of_week=5,
        job_id="weekly_stock_list_sync"
    )

    # 注册每周同花顺板块同步 (周六 03:00)
    scheduler.add_cron_job(
        job_funcs.weekly_ths_sector_sync_job,
        hour=3,
        minute=0,
        day_of_week=5,
        job_id="weekly_ths_sector_sync"
    )

    # 注册每周限售股解禁同步 (周六 04:00)
    scheduler.add_cron_job(
        job_funcs.weekly_restricted_release_job,
        hour=4,
        minute=0,
        day_of_week=5,
        job_id="weekly_restricted_release"
    )

    # 注册每周财务报表同步任务 (周六 05:00)
    scheduler.add_cron_job(
        job_funcs.weekly_financial_report_sync_job,
        hour=5,
        minute=0,
        day_of_week=5,
        job_id="weekly_financial_report_sync"
    )

    # 注册每日增量财务报表同步任务 (20:00)
    scheduler.add_daily_job(
        job_funcs.daily_financial_incremental_sync_job,
        hour=20,
        minute=0,
        job_id="daily_financial_incremental_sync"
    )
    
    await scheduler.start()
    
    yield
    
    # 关闭调度器
    await scheduler.stop()
    await db.disconnect()
    logger.info("AkShare API 服务关闭")


app = FastAPI(
    title="AkShare API",
    description="股票财务、估值、龙虎榜数据服务",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next):
    """添加 request_id 和请求日志"""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    
    from app.utils.logger import request_id_var
    token = request_id_var.set(request_id)
    
    start_time = time.time()
    try:
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)
        
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else "unknown",
        }
        logger.info(f"Request completed", extra={"extra_data": log_data, "request_id": request_id})
        
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_var.reset(token)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "ERROR", "message": str(exc.detail), "request_id": request_id}},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unexpected error: {exc}", extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "服务内部错误", "request_id": request_id}},
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# 注册路由
from app.api import finance, market, scheduler_api, information, metadata

# ... (omitted)

# 注册路由
app.include_router(finance.router, prefix="/api/v1", tags=["财务数据"])
app.include_router(market.router, prefix="/api/v1", tags=["市场数据"])
app.include_router(scheduler_api.router, prefix="/api/v1", tags=["任务调度"])
app.include_router(information.router, prefix="/api/v1", tags=["信息维度"])
app.include_router(metadata.router, prefix="/api/v1", tags=["元数据管理"])
