from fastapi import APIRouter, Query, HTTPException
from app.services.scheduler_proxy import SchedulerProxyService

router = APIRouter()
scheduler_service = SchedulerProxyService()


@router.get("/jobs")
async def get_all_jobs():
    """获取所有调度任务 (跨容器聚合 + 本地)"""
    try:
        # 1. 获取远程任务
        result = await scheduler_service.get_all_jobs()
        remote_jobs = result.get("jobs", [])

        # 2. 获取本地任务
        from app.scheduler import get_scheduler_instance
        local_scheduler = get_scheduler_instance()
        local_jobs = []
        if local_scheduler:
            raw_jobs = local_scheduler.get_jobs()
            # 格式化为统一结构
            for job in raw_jobs:
                job["container"] = "stock-manager"  # 标记来源
                local_jobs.append(job)

        return {"jobs": local_jobs + remote_jobs}
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


@router.get("/tasks", tags=["任务"])
async def get_tasks():
    """获取任务列表 (适配前端规范)"""
    try:
        jobs_data = await scheduler_service.get_all_jobs()
        jobs = jobs_data.get("jobs", [])

        # 任务分类逻辑
        # 盘前: pre_market_gate, heartbeats
        # 盘中: realtime, monitor
        # 盘后: comprehensive, sync, remediate
        def get_category(job_id: str) -> str:
            job_id = job_id.lower()
            if any(k in job_id for k in ["pre_market", "heartbeat", "health"]):
                return "pre_market"
            if any(k in job_id for k in ["realtime", "monitor", "tick"]):
                return "mid_market"
            if any(
                k in job_id for k in [
                    "sync",
                    "kline",
                    "remediate",
                    "factor",
                    "comprehensive"]):
                return "post_market"
            return "post_market"  # 默认归类为盘后

        tasks = []
        for job in jobs:
            job_id = job.get("id")
            tasks.append({
                "id": job_id,
                "name": job.get("name", job_id),
                "category": get_category(job_id),
                "enabled": not job.get("paused", False),
                "schedule": job.get("trigger", "Unknown"),
                "next_run": job.get("next_run_time"),
                "last_status": "SUCCESS" if job.get("next_run_time") else "PENDING"
            })
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")
