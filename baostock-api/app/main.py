import uuid
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

import baostock as bs

from app.api import kline, index, valuation, sync, scheduler as scheduler_api, logs, collect
from app.utils.logger import setup_logger
from app.utils.database import db
from app.services.baostock_service import BaoStockService
from app.services.collection_service import CollectionService

# 初始化日志
logger = setup_logger("baostock-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 管理BaoStock连接"""
    # 初始化 Service
    service = BaoStockService()
    app.state.baostock_service = service
    
    # 初始化 CollectionService
    collection_service = CollectionService(service)
    app.state.collection_service = collection_service
    
    # 尝试初始登录 (非强制)
    try:
        await service._ensure_connection()
    except Exception as e:
        logger.warning(f"BaoStock 初始连接失败: {e}，将在首次请求时重试")
    
    # 初始化数据库连接池
    try:
        await db.connect()
    except Exception as e:
        logger.error(f"数据库连接池启动失败: {e}")
    
    # 初始化并启动调度器
    scheduler = None
    try:
        from app.scheduler import TaskScheduler, set_scheduler_instance
        from app.scheduler.config import SCHEDULER_CONFIG
        from app.scheduler import jobs as job_funcs
        
        if SCHEDULER_CONFIG["enabled"]:
            scheduler = TaskScheduler(timezone=SCHEDULER_CONFIG["timezone"])
            set_scheduler_instance(scheduler)
            
            # 动态注册配置的任务
            for job_name, config in SCHEDULER_CONFIG["jobs"].items():
                if not config.get("enabled"): continue
                
                # 寻找匹配的函数
                func = getattr(job_funcs, f"{job_name}_job", None)
                if not func:
                    logger.warning(f"找不到任务解析函数: {job_name}_job")
                    continue
                
                if "hour" in config:
                    scheduler.add_daily_job(
                        func=func,
                        hour=config["hour"],
                        minute=config.get("minute", 0),
                        job_id=job_name
                    )
                elif "interval_seconds" in config:
                    scheduler.add_interval_job(
                        func=func,
                        seconds=config["interval_seconds"],
                        job_id=job_name
                    )
            
            await scheduler.start()
            logger.info("任务调度器配置加载完毕")
    except Exception as e:
        logger.error(f"调度器启动失败: {e}", exc_info=True)

    yield
    
    # 关闭调度器
    if scheduler:
        logger.info("正在关闭任务调度器...")
        await scheduler.stop()
    
    # 关闭数据库连接池
    await db.disconnect()
    
    # 关闭时登出
    try:
        bs.logout()
        logger.info("BaoStock API 服务关闭")
    except:
        pass


app = FastAPI(
    title="BaoStock API",
    description="股票K线、指数成分、行业分类数据服务",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next):
    """添加 request_id 和请求日志"""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    
    # 设置 ContextVar 用于日志追踪
    from app.utils.logger import request_id_var
    token = request_id_var.set(request_id)
    
    start_time = time.time()
    try:
        response = await call_next(request)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 记录请求日志
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
        # 重置 ContextVar
        request_id_var.reset(token)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """统一HTTP异常处理"""
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.detail if isinstance(exc.detail, str) else "ERROR",
                "message": str(exc.detail),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unexpected error: {exc}", extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务内部错误",
                "request_id": request_id,
            }
        },
    )


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


# 注册路由
app.include_router(kline.router, prefix="/api/v1", tags=["K线数据"])
app.include_router(index.router, prefix="/api/v1", tags=["指数与行业"])
app.include_router(valuation.router, prefix="/api/v1", tags=["估值数据"])
app.include_router(sync.router, prefix="/api/v1", tags=["数据同步"])
app.include_router(scheduler_api.router, prefix="/api/v1", tags=["任务调度"])
app.include_router(collect.router, prefix="/api/v1", tags=["远程修复"])
app.include_router(logs.router, prefix="/api/v1", tags=["执行日志"])
