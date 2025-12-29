"""
任务调度器核心类
基于 APScheduler AsyncIOScheduler
"""
import asyncio
import logging
import os
import time
from typing import Optional, Dict, Any, Callable, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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
        self._current_running_jobs = set()
        self._job_summaries = {}  # 保存手动设置的任务摘要 (V1.2+ 需求)
        logger.info(f"TaskScheduler 初始化完成，时区: {timezone}")

    def update_job_summary(self, job_id: str, summary: str):
        """更新任务的进度摘要 (V1.2+ 需求)"""
        self._job_summaries[job_id] = summary
    
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
            
            # 定义包装器来跟踪执行状态
            async def run_and_track():
                if not hasattr(self, "_current_running_jobs"):
                    self._current_running_jobs = set()
                self._current_running_jobs.add(job_id)
                try:
                    if asyncio.iscoroutinefunction(func):
                        await func(*args, **kwargs)
                    else:
                        await asyncio.to_thread(func, *args, **kwargs)
                finally:
                    self._current_running_jobs.remove(job_id)

            asyncio.create_task(run_and_track())
            return True
        except Exception as e:
            logger.error(f"手动触发任务失败 {job_id}: {e}")
            return False

    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """获取所有任务列表 (适配前端规范 V1.2)"""
        if not hasattr(self, "_current_running_jobs"):
            self._current_running_jobs = set()
            
        jobs = []
        for job in self.scheduler.get_jobs():
            # 状态逻辑: 运行中 > 暂停 > 激活
            status = "active"
            if job.id in self._current_running_jobs:
                status = "running"
            elif not job.next_run_time:
                status = "paused"
                
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
                "status": status
            })
        return jobs
    
    async def get_job_logs(self, job_id: str, limit: int = 50) -> Dict[str, Any]:
        """读取任务关联的最新日志并提取摘要 (适配 V1.2)"""
        log_file = "/app/logs/app.log"
        if not os.path.exists(log_file):
            log_file = "logs/app.log"
            
        default_resp = {"logs": ["暂无日志记录"], "summary": "准备就绪"}
        if not os.path.exists(log_file):
            return default_resp
            
        try:
            # 简单实现：读取最后 N 行并在内存中根据 job_id 简单过滤
            # 使用 asyncio.create_subprocess_exec 避免阻塞
            proc = await asyncio.create_subprocess_exec(
                'tail', '-n', str(limit * 5), log_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"读取日志失败: {stderr.decode()}")
                return default_resp

            lines = stdout.decode().splitlines()
            
            # 过滤属于该任务的日志
            filtered = [l for l in lines if job_id in l or "scheduler" in l.lower()]
            final_logs = filtered[-limit:] if filtered else lines[-limit:]
            
            # 提取摘要
            # 1. 优先使用手动设置的摘要
            summary = self._job_summaries.get(job_id)
            
            # 2. 从最后一条 JSON 日志中提取 message 作为摘要
            if not summary and final_logs:
                last_line = final_logs[-1]
                if "{" in last_line and "}" in last_line:
                    try:
                        import json
                        log_data = json.loads(last_line)
                        summary = log_data.get("message", "运行中...")
                    except:
                        summary = last_line
                else:
                    summary = last_line

            return {
                "logs": final_logs,
                "summary": str(summary)[:100] if summary else "正常运行"
            }
        except Exception as e:
            return {"logs": [f"读取日志失败: {e}"], "summary": "获取摘要失败"}
    
    def get_job_detail(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取单个任务详情"""
        job = self.scheduler.get_job(job_id)
        if not job:
            return None
        
        status = "active"
        if hasattr(self, "_current_running_jobs") and job_id in self._current_running_jobs:
            status = "running"
        elif not job.next_run_time:
            status = "paused"

        return {
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
            "func": job.func.__name__,
            "status": status,
            "pending": job.pending,
        }
    
    @property
    def is_running(self) -> bool:
        """调度器是否正在运行"""
        return self._started
