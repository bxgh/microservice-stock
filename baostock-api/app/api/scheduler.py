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
    """获取全系统聚合任务列表"""
    service = request.app.state.baostock_service
    jobs = await service.get_all_container_jobs()
    return {
        "total": len(jobs),
        "jobs": jobs
    }


@router.post("/scheduler/jobs/{job_id}/{action}")
async def handle_job_action(job_id: str, action: str, request: Request, container: str = "baostock-api"):
    """
    处理任务操作 (pause, resume, run)
    支持跨容器转发
    """
    if action not in ["pause", "resume", "run"]:
        raise HTTPException(status_code=400, detail="不支持的操作")
        
    service = request.app.state.baostock_service
    success = await service.perform_remote_job_action(container, job_id, action)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"对容器 {container} 的任务 {job_id} 执行 {action} 失败")
    
    return {"message": f"操作 {action} 已成功发送至 {container}"}
