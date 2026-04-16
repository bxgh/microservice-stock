import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from app.api import endpoints
from app.utils.logger import setup_logger, request_id_var
from app.services.tushare_service import TushareService

# 初始化日志
logger = setup_logger("tushare-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Tushare API 服务启动")
    
    # 初始化 Service
    app.state.tushare_service = TushareService()
    
    yield
    
    logger.info("Tushare API 服务关闭")

app = FastAPI(
    title="Tushare API",
    description="Tushare Pro 数据集成服务 (200积分限制版)",
    version="1.0.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next):
    """添加 request_id 和请求日志"""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    
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
app.include_router(endpoints.router, prefix="/api/v1", tags=["Tushare数据"])
