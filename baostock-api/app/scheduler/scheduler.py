"""
任务调度器核心类
基于 APScheduler AsyncIOScheduler
"""
import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.scheduler.config import SCHEDULER_CONFIG

logger = logging.getLogger(__name__)

# 全局调度器实例
_scheduler_instance: Optional["TaskScheduler"] = None


def get_scheduler_instance() -> Optional["TaskScheduler"]:
    """获取全局调度器实例"""
    return _scheduler_instance


def set_scheduler_instance(scheduler: "TaskScheduler") -> None:
    """设置全局调度器实例"""
    global _scheduler_instance
    _scheduler_instance = scheduler


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, timezone: str = "Asia/Shanghai"):
        """
        初始化调度器
        
        Args:
            timezone: 时区设置
        """
        self.scheduler = AsyncIOScheduler(timezone=timezone)
        self.timezone = timezone
        self._started = False
        logger.info(f"TaskScheduler 初始化完成，时区: {timezone}")
    
    async def start(self):
        """启动调度器"""
        if not self._started:
            self.scheduler.start()
            self._started = True
            logger.info("TaskScheduler 已启动")
    
    async def stop(self):
        """停止调度器"""
        if self._started:
            self.scheduler.shutdown(wait=True)
            self._started = False
            logger.info("TaskScheduler 已停止")
    
    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        **kwargs
    ) -> str:
        """
        添加 cron 定时任务
        
        Args:
            func: 任务函数
            job_id: 任务ID
            hour: 小时 (0-23)
            minute: 分钟 (0-59)
            second: 秒 (0-59)
            
        Returns:
            任务ID
        """
        # 如果任务已存在，先删除
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"删除已存在的任务: {job_id}")
        
        try:
            trigger = CronTrigger(hour=hour, minute=minute, second=second, timezone=self.timezone)
            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                name=f"{func.__name__}_{hour:02d}:{minute:02d}",
                replace_existing=True,
                **kwargs
            )
            logger.info(f"添加cron任务: {job_id}, 执行时间: {hour:02d}:{minute:02d}:{second:02d}")
            return job_id
        except Exception as e:
            logger.error(f"添加cron任务失败: {e}", exc_info=True)
            raise
    
    def add_daily_job(
        self,
        func: Callable,
        hour: int,
        minute: int = 0,
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        添加每日定时任务
        
        Args:
            func: 任务函数
            hour: 小时 (0-23)
            minute: 分钟 (0-59)
            job_id: 任务ID，默认使用函数名
            
        Returns:
            任务ID
        """
        if job_id is None:
            job_id = f"daily_{func.__name__}"
        
        return self.add_cron_job(func, job_id, hour=hour, minute=minute, **kwargs)
    
    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        **kwargs
    ) -> str:
        """
        添加间隔任务
        
        Args:
            func: 任务函数
            job_id: 任务ID
            seconds: 间隔秒数
            minutes: 间隔分钟数
            hours: 间隔小时数
            
        Returns:
            任务ID
        """
        total_interval = seconds + minutes * 60 + hours * 3600
        
        if total_interval <= 0:
            raise ValueError("间隔时间必须大于0")
        
        # 如果任务已存在，先删除
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        try:
            trigger = IntervalTrigger(seconds=total_interval, timezone=self.timezone)
            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                name=f"每{total_interval}秒_{func.__name__}",
                replace_existing=True,
                **kwargs
            )
            logger.info(f"添加间隔任务: {job_id}, 间隔: {total_interval}秒")
            return job_id
        except Exception as e:
            logger.error(f"添加间隔任务失败: {e}", exc_info=True)
            raise
    
    def add_hourly_job(
        self,
        func: Callable,
        minute: int = 0,
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        添加每小时定时任务
        
        Args:
            func: 任务函数
            minute: 分钟 (0-59)
            job_id: 任务ID
            
        Returns:
            任务ID
        """
        if job_id is None:
            job_id = f"hourly_{func.__name__}"
        
        # 使用 cron 表达式：每小时的第 minute 分钟
        return self.add_cron_job(func, job_id, hour="*", minute=minute, **kwargs)
    
    def remove_job(self, job_id: str) -> bool:
        """
        删除任务
        
        Args:
            job_id: 任务ID
            
        Returns:
            是否成功删除
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"删除任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"删除任务失败 {job_id}: {e}")
            return False
    
    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"暂停任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"暂停任务失败 {job_id}: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"恢复任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"恢复任务失败 {job_id}: {e}")
            return False

    async def run_job_now(self, job_id: str) -> bool:
        """立即执行任务"""
        job = self.scheduler.get_job(job_id)
        if not job:
            return False
            
        try:
            # 获取任务函数和参数
            func = job.func
            args = job.args
            kwargs = job.kwargs
            
            logger.info(f"手动触发任务执行: {job_id}")
            
            # 异步执行，不阻塞 API
            if asyncio.iscoroutinefunction(func):
                asyncio.create_task(func(*args, **kwargs))
            else:
                # 同步函数在线程池执行
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, func, *args, **kwargs)
                
            return True
        except Exception as e:
            logger.error(f"手动触发任务失败 {job_id}: {e}")
            return False

    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """获取所有任务列表"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return jobs
    
    def get_job_detail(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取单个任务详情"""
        job = self.scheduler.get_job(job_id)
        if not job:
            return None
        
        return {
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
            "func": job.func.__name__,
            "pending": job.pending,
        }
    
    @property
    def is_running(self) -> bool:
        """调度器是否正在运行"""
        return self._started
