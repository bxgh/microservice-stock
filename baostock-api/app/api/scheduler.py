"""
调度器管理 API
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/scheduler/status")
async def get_scheduler_status(request: Request):
    """获取调度器状态"""
    from app.scheduler import get_scheduler_instance
    
    scheduler = get_scheduler_instance()
    if not scheduler:
        raise HTTPException(status_code=503, detail="调度器未初始化")
    
    return {
        "running": scheduler.is_running,
        "timezone": scheduler.timezone,
        "jobs_count": len(scheduler.get_jobs())
    }


@router.get("/scheduler/jobs")
async def list_jobs(request: Request):
    """获取所有任务列表"""
    from app.scheduler import get_scheduler_instance
    
    scheduler = get_scheduler_instance()
    if not scheduler:
        raise HTTPException(status_code=503, detail="调度器未初始化")
    
    jobs = scheduler.get_jobs()
    return {
        "total": len(jobs),
        "jobs": jobs
    }


@router.get("/scheduler/jobs/{job_id}")
async def get_job_detail(job_id: str, request: Request):
    """获取单个任务详情"""
    from app.scheduler import get_scheduler_instance
    
    scheduler = get_scheduler_instance()
    if not scheduler:
        raise HTTPException(status_code=503, detail="调度器未初始化")
    
    job = scheduler.get_job_detail(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")
    
    return job


@router.post("/scheduler/jobs/{job_id}/pause")
async def pause_job(job_id: str, request: Request):
    """暂停任务"""
    from app.scheduler import get_scheduler_instance
    
    scheduler = get_scheduler_instance()
    if not scheduler:
        raise HTTPException(status_code=503, detail="调度器未初始化")
    
    success = scheduler.pause_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"暂停任务失败: {job_id}")
    
    return {"message": f"任务 {job_id} 已暂停"}


@router.post("/scheduler/jobs/{job_id}/resume")
async def resume_job(job_id: str, request: Request):
    """恢复任务"""
    from app.scheduler import get_scheduler_instance
    
    scheduler = get_scheduler_instance()
    if not scheduler:
        raise HTTPException(status_code=503, detail="调度器未初始化")
    
    success = scheduler.resume_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"恢复任务失败: {job_id}")
    
    return {"message": f"任务 {job_id} 已恢复"}
