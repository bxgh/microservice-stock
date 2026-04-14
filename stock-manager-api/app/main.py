import uuid
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from app.api import (
    metadata, audit, scheduler, ops, system, dashboard, 
    shareholders, chips, game, information, commands, task_commands, data_audit, suspension
)
from app.utils.logger import setup_logger, request_id_var
from app.utils.database import db
from app.utils.http_client import http_client

# 初始化日志
logger = setup_logger("stock-manager")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库连接
    try:
        await db.connect()
    except Exception as e:
        logger.error(f"数据库连接池启动失败: {e}")
    
    # 初始化并启动调度器
    scheduler = None
    try:
        from app.scheduler import TaskScheduler, set_scheduler_instance
        from app.scheduler import jobs as job_funcs
        
        # 1. 初始化
        scheduler = TaskScheduler(timezone="Asia/Shanghai")
        set_scheduler_instance(scheduler)
        
        
        # 2. 注册早盘停牌数据同步任务 (每天 09:15)
        scheduler.add_daily_job(
            job_funcs.daily_suspension_morning_sync_job,
            hour=9,
            minute=15,
            job_id="daily_suspension_morning_sync"
        )

        # 3. 注册早盘业绩预告同步任务 (每天 08:45)
        scheduler.add_daily_job(
            job_funcs.daily_performance_forecast_sync_job,
            hour=8,
            minute=45,
            job_id="daily_performance_forecast_sync"
        )
        
        # 3. 启动
        await scheduler.start()
        logger.info("Stock-Manager 内部调度器已启动")
        
    except Exception as e:
        logger.error(f"调度器启动失败: {e}", exc_info=True)

    yield
    
    # 关闭调度器
    if scheduler:
        await scheduler.stop()
    
    # 关闭时清理资源
    await db.disconnect()
    await http_client.close()
    logger.info("Stock-Manager API 服务关闭")

app = FastAPI(
    title="Stock-Manager API",
    description="数据溯源管理系统 - 业务中台",
    version="1.0.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next):
    """添加 request_id 和请求日志"""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    
    # 设置 ContextVar
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
app.include_router(metadata.router, prefix="/api/v1/metadata", tags=["元数据"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["审计"])
app.include_router(scheduler.router, prefix="/api/v1/scheduler", tags=["调度"])
app.include_router(suspension.router, prefix="/api/v1", tags=["停牌数据"])
app.include_router(ops.router, prefix="/api/v1/ops", tags=["运维"])
app.include_router(system.router, prefix="/api/v1/system", tags=["系统"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["仪表盘"])
app.include_router(commands.router, prefix="/api/v1/commands", tags=["命令"])
app.include_router(task_commands.router, prefix="/api/v1/task-commands", tags=["任务指令"])
app.include_router(data_audit.router, prefix="/api/v1/data-audits", tags=["数据审计"])
app.include_router(shareholders.router, prefix="/api/v1/shareholders", tags=["股东数据"])
app.include_router(chips.router, prefix="/api/v1/chips", tags=["筹码维度同步"])
app.include_router(game.router, prefix="/api/v1/game", tags=["博弈维度同步"])
app.include_router(information.router, prefix="/api/v1/information", tags=["信息维度同步"])

