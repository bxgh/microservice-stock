from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("baostock-api.api.sync")

@router.post("/sync/kline/{code}")
async def sync_stock_kline(
    request: Request,
    code: str,
    background_tasks: BackgroundTasks,
    start_date: Optional[str] = Query("1990-12-19", description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query("", description="结束日期 YYYY-MM-DD (默认至今)"),
    frequency: str = Query("d", description="频率: d, w, m"),
    adjust: str = Query("2", description="复权: 1后复权, 2前复权, 3不复权")
):
    """
    同步个股历史 K 线数据到 MySQL (支持后台异步执行)
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.baostock_service
    
    # 立即返回响应，后台执行同步
    async def do_sync():
        logger.info(f"开始同步任务: code={code}, start={start_date}", extra={"request_id": request_id})
        result = await service.sync_kline_to_db(
            code=code,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjust=adjust
        )
        if result["success"]:
            logger.info(f"同步任务成功: {code}, 数量={result['count']}, 耗时={result['performance']['total_ms']}ms", extra={"request_id": request_id})
        else:
            logger.error(f"同步任务失败: {code}, 原因={result.get('error')}", extra={"request_id": request_id})

    background_tasks.add_task(do_sync)
    
    return {
        "message": f"股票 {code} 的同步任务已提交至后台处理",
        "request_id": request_id
    }

@router.post("/sync/full")
async def sync_full_market(
    request: Request,
    background_tasks: BackgroundTasks,
    start_date: Optional[str] = Query("1990-12-19", description="开始日期 YYYY-MM-DD")
):
    """
    一键同步全市场 A 股 K 线数据到 MySQL
    """
    service = request.app.state.baostock_service
    status = service.get_sync_status()
    
    if status["running"]:
        return {"message": "全市场同步任务已在运行中", "status": status}
    
    async def do_full_sync():
        logger.info(f"后台启动全市场K线同步任务, start_date={start_date}")
        try:
            await service.sync_all_stocks_kline(start_date=start_date)
        except Exception as e:
            logger.error(f"全市场K线同步启动失败: {e}")

    background_tasks.add_task(do_full_sync)
    
    return {
        "message": "全市场同步任务已启动",
        "total_estimated": status.get("total", "calculating...")
    }

@router.get("/sync/status")
async def get_sync_status(request: Request):
    """
    获取全局同步任务状态
    """
    service = request.app.state.baostock_service
    return service.get_sync_status()

@router.post("/sync/reset")
async def reset_sync_progress(request: Request):
    """
    强制重置同步进度 (下次任务将从 0 开始)
    """
    service = request.app.state.baostock_service
    await service.reset_sync_progress()
    return {"message": "同步进度已重置"}

@router.post("/sync/adjust_factor/full")
async def sync_full_market_adjust_factor(
    request: Request,
    background_tasks: BackgroundTasks,
    start_date: Optional[str] = Query("1990-01-01", description="开始日期 YYYY-MM-DD")
):
    """
    一键同步全市场 A 股复权因子数据到 MySQL
    """
    service = request.app.state.baostock_service
    status = service.get_adjust_sync_status()
    
    if status["running"]:
        return {"message": "全市场复权因子同步任务已在运行中", "status": status}
    
    async def do_full_adjust_sync():
        logger.info(f"后台启动全市场复权因子同步任务, start_date={start_date}")
        try:
            await service.sync_all_stocks_adjust_factor(start_date=start_date)
        except Exception as e:
            logger.error(f"全市场复权因子同步启动失败: {e}")

    background_tasks.add_task(do_full_adjust_sync)
    
    return {
        "message": "全市场复权因子同步任务已启动",
        "total_estimated": status.get("total", "calculating...")
    }

@router.get("/sync/adjust_factor/status")
async def get_adjust_sync_status(request: Request):
    """
    获取复权因子同步任务状态
    """
    service = request.app.state.baostock_service
    return service.get_adjust_sync_status()

@router.post("/sync/adjust_factor/{code}")
async def sync_stock_adjust_factor(
    request: Request,
    code: str,
    background_tasks: BackgroundTasks,
    start_date: Optional[str] = Query("1990-01-01", description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query("", description="结束日期 YYYY-MM-DD (默认至今)")
):
    """
    同步个股历史复权因子数据到 MySQL (支持后台异步执行)
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.baostock_service
    
    async def do_sync():
        logger.info(f"开始复权因子同步任务: code={code}, start={start_date}", extra={"request_id": request_id})
        result = await service.sync_adjust_factor_to_db(
            code=code,
            start_date=start_date,
            end_date=end_date
        )
        if result["success"]:
            logger.info(f"复权因子同步任务成功: {code}, 数量={result['count']}, 耗时={result.get('performance', {}).get('total_ms', 0)}ms", extra={"request_id": request_id})
        else:
            logger.error(f"复权因子同步任务失败: {code}, 原因={result.get('error')}", extra={"request_id": request_id})

    background_tasks.add_task(do_sync)
    
@router.get("/sync/verify/daily")
async def verify_daily_sync(
    request: Request,
    date: Optional[str] = Query(None, description="要校验的日期 YYYY-MM-DD，默认今天")
):
    """
    核验每日数据下载完整性 (对比全市场 A 股总数)
    """
    service = request.app.state.baostock_service
    report = await service.verify_daily_data_completeness(target_date=date)
    return report
