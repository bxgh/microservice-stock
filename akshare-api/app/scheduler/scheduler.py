import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler_instance: Optional["TaskScheduler"] = None

def get_scheduler_instance() -> Optional["TaskScheduler"]:
    return _scheduler_instance

def set_scheduler_instance(scheduler: "TaskScheduler") -> None:
    global _scheduler_instance
    _scheduler_instance = scheduler

class TaskScheduler:
    def __init__(self, timezone: str = "Asia/Shanghai"):
        self.scheduler = AsyncIOScheduler(timezone=timezone)
        self.timezone = timezone
        self._started = False
    
    async def start(self):
        if not self._started:
            self.scheduler.start()
            self._started = True
    
    async def stop(self):
        if self._started:
            self.scheduler.shutdown(wait=True)
            self._started = False
    
    def add_cron_job(self, func: Callable, job_id: str, hour: int = 0, minute: int = 0, second: int = 0, **kwargs) -> str:
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        trigger = CronTrigger(hour=hour, minute=minute, second=second, timezone=self.timezone)
        self.scheduler.add_job(func, trigger=trigger, id=job_id, name=f"{func.__name__}", replace_existing=True, **kwargs)
        return job_id
    
    def add_interval_job(self, func: Callable, job_id: str, seconds: int = 0, **kwargs) -> str:
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        trigger = IntervalTrigger(seconds=seconds, timezone=self.timezone)
        self.scheduler.add_job(func, trigger=trigger, id=job_id, name=f"{func.__name__}", replace_existing=True, **kwargs)
        return job_id

    def pause_job(self, job_id: str) -> bool:
        try:
            self.scheduler.pause_job(job_id)
            return True
        except:
            return False
            
    def resume_job(self, job_id: str) -> bool:
        try:
            self.scheduler.resume_job(job_id)
            return True
        except:
            return False

    async def run_job_now(self, job_id: str) -> bool:
        job = self.scheduler.get_job(job_id)
        if not job: return False
        func = job.func
        if asyncio.iscoroutinefunction(func):
            asyncio.create_task(func(*job.args, **job.kwargs))
        else:
            asyncio.get_event_loop().run_in_executor(None, func, *job.args, **job.kwargs)
        return True

    def get_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
                "status": "active" if job.next_run_time else "paused"
            })
        return jobs
