from fastapi import APIRouter, HTTPException, Request
from app.scheduler import get_scheduler_instance

router = APIRouter()

@router.get("/scheduler/jobs")
async def get_jobs():
    scheduler = get_scheduler_instance()
    if not scheduler:
        return {"total": 0, "jobs": []}
    jobs = scheduler.get_jobs()
    return {"total": len(jobs), "jobs": jobs}

@router.post("/scheduler/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    scheduler = get_scheduler_instance()
    if not scheduler or not scheduler.pause_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found or failed to pause")
    return {"message": f"Job {job_id} paused"}

@router.post("/scheduler/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    scheduler = get_scheduler_instance()
    if not scheduler or not scheduler.resume_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found or failed to resume")
    return {"message": f"Job {job_id} resumed"}

@router.post("/scheduler/jobs/{job_id}/run")
async def run_job(job_id: str):
    scheduler = get_scheduler_instance()
    if not scheduler or not await scheduler.run_job_now(job_id):
        raise HTTPException(status_code=404, detail="Job not found or failed to run")
    return {"message": f"Job {job_id} triggered"}
