from fastapi import APIRouter, HTTPException, Query, Request
from app.services.finance_service import FinanceService
from app.schemas.finance import (
    FullFinancialReportResponse, SyncFinanceResult,
    FinancialIndicatorsListResponse, SyncFinanceIndicatorsResult
)
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("stock-manager.api.finance")
finance_service = FinanceService()


@router.get("/reports/{code}", response_model=FullFinancialReportResponse)
async def get_financial_reports(
    code: str,
    limit: int = Query(40, description="返回的历史报告期数量", ge=1, le=100)
):
    """
    获取个股的历史财务三大会计报表 (资产负债表、利润表、现金流量表)

    - **code**: 股票代码 (如 600519.SH)
    - **limit**: 获取的最近报告期数量
    """
    try:
        data = await finance_service.get_financial_reports(code, limit)
        if not data["balance_sheets"] and not data["income_statements"]:
            raise HTTPException(
                status_code=404,
                detail=f"未找到代码 {code} 的财务报表数据")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取财务报表接口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/{code}", response_model=SyncFinanceResult)
async def sync_financial_reports(request: Request, code: str):
    """
    触发将特定个股的历史财务报表从数据源同步至 MySQL

    - **code**: 股票代码 (如 600519.SH)
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"开始同步财务报表: {code}", extra={"request_id": request_id})

    try:
        result = await finance_service.sync_financial_reports(code)
        if not result.get("success"):
            raise HTTPException(
                status_code=500, detail=result.get(
                    "message", "Sync failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"同步财务报表接口失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/{code}",
            response_model=FinancialIndicatorsListResponse)
async def get_financial_indicators(
    code: str,
    limit: int = Query(40, description="返回的历史数据数量", ge=1, le=100)
):
    """
    获取个股的历史财务衍生指标 (ROE, ROA, 毛利率, EPS等)
    """
    try:
        data = await finance_service.get_financial_indicators(code, limit)
        if not data["indicators"]:
            raise HTTPException(
                status_code=404,
                detail=f"未找到代码 {code} 的财务衍生指标数据")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取财务衍生指标接口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-indicators/{code}",
             response_model=SyncFinanceIndicatorsResult)
async def sync_financial_indicators(request: Request, code: str):
    """
    触发个股财务衍生指标同步
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"开始同步财务衍生指标: {code}", extra={"request_id": request_id})

    try:
        result = await finance_service.sync_financial_indicators(code)
        if not result.get("success"):
            raise HTTPException(
                status_code=500, detail=result.get(
                    "message", "Sync failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"同步财务衍生指标接口失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-all-indicators")
async def sync_all_financial_indicators(request: Request):
    """
    触发全市场财务衍生指标同步任务 (后台执行)
    """
    from app.scheduler.scheduler import get_scheduler_instance
    scheduler = get_scheduler_instance()

    if not scheduler:
        raise HTTPException(status_code=500, detail="调度器未初始化")

    job_id = "weekly_finance_indicators_sync"
    success = await scheduler.run_job_now(job_id)

    if success:
        return {"message": "全市场财务衍生指标同步任务已启动 (后台运行)", "job_id": job_id}
    else:
        raise HTTPException(status_code=500, detail="任务启动失败，请检查调度器状态")
