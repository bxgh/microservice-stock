from fastapi import APIRouter, Query, HTTPException
from app.services.scheduler_proxy import SchedulerProxyService

router = APIRouter()
scheduler_service = SchedulerProxyService()

@router.get("/jobs")
async def get_all_jobs():
    """获取所有调度任务 (跨容器聚合)"""
    try:
        return await scheduler_service.get_all_jobs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")

@router.post("/jobs/{job_id}/{action}")
async def control_job(
    job_id: str,
    action: str,
    container: str = Query(..., description="目标容器: baostock/akshare/pywencai")
):
    """控制任务 (pause/resume/run)"""
    if action not in ["pause", "resume", "run"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    try:
        return await scheduler_service.control_job(container, job_id, action)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")

@router.get("/jobs/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    container: str = Query(..., description="目标容器"),
    lines: int = Query(50, description="返回行数")
):
    """获取任务日志"""
    try:
        return await scheduler_service.get_job_logs(container, job_id, lines)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")
