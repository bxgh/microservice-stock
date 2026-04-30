import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from app.api import kline, quote, stock_info, market, calendar, auth, diary, user
from app.utils.logger import setup_logger, request_id_var
from app.utils.database import db

# 初始化日志
logger = setup_logger("gateway")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库连接
    try:
        await db.connect()
        logger.info("Gateway service started and DB connected")
    except Exception as e:
        logger.error(f"数据库连接池启动失败: {e}")
    
    yield
    
    # 关闭时清理资源
    await db.disconnect()
    logger.info("Gateway service stopped")

app = FastAPI(
    title="WXCH Gateway",
    description="Direct MySQL API for Microservice Stock",
    version="2.0.0",
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
        logger.info("Request completed", extra={"extra_data": log_data, "request_id": request_id})
        
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_var.reset(token)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "request_id": request_id
            }
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error",
                "request_id": request_id
            }
        },
    )

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "wxch-gateway"}

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证授权"])
app.include_router(user.router, prefix="/api/v1/user", tags=["用户系统"])
app.include_router(diary.router, prefix="/api/v1/diaries", tags=["股市日记"])
app.include_router(kline.router, prefix="/api/v1/stocks", tags=["股票数据"])
app.include_router(quote.router, prefix="/api/v1/stocks", tags=["股票数据"])
app.include_router(stock_info.router, prefix="/api/v1/stocks", tags=["个股详情"])
app.include_router(market.router, prefix="/api/v1/market", tags=["市场纵览"])
app.include_router(calendar.router, prefix="/api/v1/calendar", tags=["交易日历"])

# 静态首页或 404 处理
@app.get("/")
async def root():
    return {"message": "WXCH Gateway API v2.0 is running"}
