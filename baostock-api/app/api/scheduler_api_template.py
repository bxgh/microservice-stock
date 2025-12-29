from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Query
from app.scheduler import get_scheduler_instance

router = APIRouter()

@router.get("/scheduler/jobs")
async def list_jobs(request: Request):
    """获取任务列表 (符合规范 V1.2)"""
    scheduler = get_scheduler_instance()
    if not scheduler:
        raise HTTPException(status_code=503, detail="调度器未初始化")
    
    jobs = scheduler.get_jobs()
    return {
        "jobs": jobs
    }

@router.post("/scheduler/jobs/{job_id}/pause")
async def pause_job(job_id: str, request: Request):
    """暂停任务"""
    scheduler = get_scheduler_instance()
    success = scheduler.pause_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="暂停失败")
    return {"status": "ok", "message": f"Job {job_id} paused"}

@router.post("/scheduler/jobs/{job_id}/resume")
async def resume_job(job_id: str, request: Request):
    """恢复任务"""
    scheduler = get_scheduler_instance()
    success = scheduler.resume_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="恢复失败")
    return {"status": "ok", "message": f"Job {job_id} resumed"}

@router.post("/scheduler/jobs/{job_id}/run")
async def run_job(job_id: str, request: Request):
    """立即执行任务"""
    scheduler = get_scheduler_instance()
    success = await scheduler.run_job_now(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="触发失败")
    return {"status": "ok", "message": f"Job {job_id} triggered"}

@router.get("/scheduler/jobs/{job_id}/logs")
async def get_job_logs(job_id: str, lines: int = Query(50)):
    """获取任务实时日志 (适配 V1.2 Summary)"""
    scheduler = get_scheduler_instance()
    if not scheduler:
        return {"logs": ["调度器未就绪"], "summary": "未就绪"}
    
    # scheduler.get_job_logs 已经返回 {"logs": [...], "summary": "..."}
    return scheduler.get_job_logs(job_id, limit=lines)
