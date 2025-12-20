"""AkShare API 服务入口"""
import uuid
import time
import logging
import json
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from app.api import finance, market


# JSON日志配置
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "extra_data"):
            log_record.update(record.extra_data)
        return json.dumps(log_record, ensure_ascii=False)


# 配置日志
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("akshare-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("AkShare API 服务启动")
    yield
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
    
    start_time = time.time()
    
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
app.include_router(finance.router, prefix="/api/v1", tags=["财务数据"])
app.include_router(market.router, prefix="/api/v1", tags=["市场数据"])
