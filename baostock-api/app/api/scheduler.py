from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request, Query
from app.scheduler import get_scheduler_instance

router = APIRouter()

@router.get("/scheduler/jobs")
async def list_jobs(request: Request):
    """获取跨容器聚合任务列表 (符合规范 V1.2)"""
    service = request.app.state.baostock_service
    jobs = await service.get_all_container_jobs()
    return {
        "jobs": jobs
    }

@router.post("/scheduler/jobs/{job_id}/{action}")
async def handle_job_action(job_id: str, action: str, request: Request, container: str = Query("baostock-api")):
    """处理任务动作 (pause, resume, run)"""
    if action not in ["pause", "resume", "run"]:
        raise HTTPException(status_code=400, detail="不支持的操作")
        
    service = request.app.state.baostock_service
    success = await service.perform_remote_job_action(container, job_id, action)
    
    if not success:
        raise HTTPException(status_code=400, detail="操作执行失败")
        
    return {"status": "ok", "message": f"Action {action} sent to {container}"}

@router.get("/scheduler/jobs/{job_id}/logs")
async def get_job_logs(job_id: str, request: Request, container: str = Query("baostock-api"), lines: int = Query(50)):
    """获取任务实时日志 (支持跨容器转发 + Summary 提取)"""
    service = request.app.state.baostock_service
    return await service.proxy_container_job_logs(container, job_id, lines)
