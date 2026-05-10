import uuid
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from app.api import metadata, audit, scheduler, ops, system, dashboard, market_dashboard, shareholders, chips, game, information, commands, task_commands, pipelines, data_audit, suspension, monitor, finance, dq, backfill, healer
from app.api.market import router as market_router

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
        from app.scheduler import system_jobs as sys_job_funcs

        # 1. 初始化
        scheduler = TaskScheduler(timezone="Asia/Shanghai")
        set_scheduler_instance(scheduler)

        # 1.1 注册系统健康监控 (每 5 分钟)
        scheduler.add_interval_job(
            sys_job_funcs.system_health_monitor_job,
            minutes=5,
            job_id="system_health_monitor"
        )

        # 1.2 注册全生命周期就绪探测器 (每 2 分钟)
        # 职责: 08:00-09:30 探测晨间信号; 15:30-19:00 探测收盘信号; 19:00-23:00 高频探测
        scheduler.add_interval_job(
            sys_job_funcs.readiness_prober_job,
            minutes=2,
            job_id="readiness_prober"
        )

        # 2. 注册深夜维护流水线 (每日 01:00)
        # 职责: 财务指标同步、机构评级、股东数据、错峰执行
        from app.services.workflow_service import workflow_service
        import datetime
        scheduler.add_daily_job(
            workflow_service.process_maintenance_trigger,
            job_id="daily_maintenance_pipeline",
            hour=1,
            minute=0,
            args=[datetime.date.today()]
        )

        # 3. 注册流水线保底扫描任务 (23:00)
        scheduler.add_daily_job(
            sys_job_funcs.safety_workflow_scan_job,
            job_id="safety_workflow_scan",
            hour=23,
            minute=0
        )

        # 4. 注册每日任务总结报告
        # 初次总结 (23:45)
        scheduler.add_daily_job(
            sys_job_funcs.daily_pipeline_summary_job,
            job_id="daily_summary_night",
            hour=23,
            minute=45
        )
        # 最终报告 (次日 06:00)
        scheduler.add_daily_job(
            sys_job_funcs.daily_pipeline_summary_job,
            job_id="daily_summary_final",
            hour=6,
            minute=0
        )

        # 5. 注册补数扫描与处理任务
        scheduler.add_interval_job(
            sys_job_funcs.backfill_enqueue_job,
            hours=1,
            job_id="backfill_enqueue"
        )
        scheduler.add_interval_job(
            sys_job_funcs.backfill_processor_job,
            minutes=5,
            job_id="backfill_processor"
        )

        # 5. 注册每周复权因子对账任务 (每周日 05:00)
        scheduler.add_cron_job(
            job_funcs.weekly_factor_reconcile_job,
            job_id="weekly_factor_reconcile",
            day_of_week='sun',
            hour=5,
            minute=0
        )

        # 启动
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
        call_res = await call_next(request)

        duration_ms = int((time.time() - start_time) * 1000)

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": call_res.status_code,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else "unknown",
        }
        logger.info(
            f"Request completed",
            extra={
                "extra_data": log_data,
                "request_id": request_id})

        call_res.headers["X-Request-ID"] = request_id
        return call_res
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
app.include_router(
    market_dashboard.router,
    prefix="/api/v1/market/dashboard",
    tags=["市场全景"])
app.include_router(commands.router, prefix="/api/v1/commands", tags=["命令"])
app.include_router(
    task_commands.router,
    prefix="/api/v1/task-commands",
    tags=["任务指令"])
app.include_router(
    data_audit.router,
    prefix="/api/v1/data-audits",
    tags=["数据审计"])
app.include_router(
    shareholders.router,
    prefix="/api/v1/shareholders",
    tags=["股东数据"])
app.include_router(chips.router, prefix="/api/v1/chips", tags=["筹码维度同步"])
app.include_router(game.router, prefix="/api/v1/game", tags=["博弈维度同步"])
app.include_router(
    information.router,
    prefix="/api/v1/information",
    tags=["信息维度同步"])
app.include_router(monitor.router, prefix="/api/v1/monitor", tags=["监控指标"])
app.include_router(finance.router, prefix="/api/v1/finance", tags=["财务数据"])
app.include_router(market_router, prefix="/api/v1/market", tags=["行情数据"])
app.include_router(dq.router, prefix="/api/v1/dq", tags=["数据质量"])
app.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["任务状态机"])
app.include_router(backfill.router, prefix="/api/v1/backfill", tags=["补数与重算"])
app.include_router(healer.router, prefix="/api/v1", tags=["自愈修复"])
