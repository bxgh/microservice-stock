import uuid
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

import baostock as bs

from app.api import kline, index, valuation
from app.utils.logger import setup_logger
from app.services.baostock_service import BaoStockService

# 初始化日志
logger = setup_logger("baostock-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 管理BaoStock连接"""
    # 初始化 Service
    service = BaoStockService()
    app.state.baostock_service = service
    
    # 尝试初始登录 (非强制)
    try:
        await service._ensure_connection()
    except Exception as e:
        logger.warning(f"BaoStock 初始连接失败: {e}，将在首次请求时重试")
    
    yield
    
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
