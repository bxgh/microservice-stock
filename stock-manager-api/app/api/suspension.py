from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks
from app.services.suspension_service import SuspensionService
from app.utils.logger import get_logger
from datetime import datetime, timedelta

router = APIRouter()
logger = get_logger("stock-manager.api.suspension")

@router.post("/suspensions/sync")
async def sync_suspensions(
    background_tasks: BackgroundTasks,
    request: Request,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
):
    """
    同步停牌数据 (异步任务)
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    async def _run_sync(s_date, e_date, req_id):
        service = SuspensionService()
        logger.info(f"开始同步停牌数据: {s_date} ~ {e_date}", extra={"request_id": req_id})
        try:
            stats = await service.sync_date_range(s_date, e_date)
            logger.info(f"停牌数据同步完成: {stats}", extra={"request_id": req_id})
        except Exception as e:
            logger.error(f"停牌数据同步失败: {e}", extra={"request_id": req_id})

    background_tasks.add_task(_run_sync, start_date, end_date, request_id)
    
    return {"message": "同步任务已提交", "start_date": start_date, "end_date": end_date}
