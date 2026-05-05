import asyncio
import time
import traceback
import subprocess
from datetime import date
from app.utils.logger import get_logger
from app.utils.database import cloud_db, internal_db
from app.utils.alerter import alerter

logger = get_logger("stock-compute.pipeline")

class PipelineRunner:
    """通用管线执行器,支持依赖、超时、重试、断点续跑 (E3/E5)"""

    def __init__(self, pipeline_id: str, tasks: list, gate):
        self.pipeline_id = pipeline_id
        self.tasks = tasks
        self.gate = gate
        self._task_map = {t["task_id"]: t for t in tasks}

    async def run(self, biz_date: date, mode: str = "normal"):
        run_id = f"{self.pipeline_id}_{biz_date.isoformat()}"

        # 全局闸门: 整个管线占据, 期间其他重任务等待
        async with self.gate.heavy_task(run_id, timeout=7200):
            # 拓扑排序 (简化版，按列表顺序执行)
            for task in self.tasks:
                # 1. 断点续跑: 检查是否已成功
                if await self._is_done(run_id, task["task_id"]):
                    logger.info(f"[skip] {task['task_id']} 已完成")
                    continue

                # 2. 检查依赖 (简化版，仅检查前序任务是否成功)
                # ... 生产环境建议实现真正的拓扑排序

                # 3. 执行 (带重试)
                await self._execute_with_retry(run_id, task, biz_date)

    async def _is_done(self, run_id: str, task_id: str) -> bool:
        sql = "SELECT status FROM meta_pipeline_run WHERE run_id=%s AND task_id=%s"
        row = await cloud_db.fetch_one(sql, (run_id, task_id))
        return row and row["status"] == "SUCCESS"

    async def _execute_with_retry(self, run_id: str, task: dict, biz_date: date):
        max_retry = task.get("retry", 1)
        timeout = task.get("timeout_sec", 600)

        for attempt in range(max_retry + 1):
            await self._mark_status(run_id, task["task_id"], biz_date, "RUNNING", attempt)
            start_time = time.time()
            try:
                if task["type"] == "python_isolated":
                    await self._run_python_isolated(task, biz_date, timeout)
                elif task["type"] == "sql":
                    await self._run_sql(task, biz_date, timeout)
                else:
                    # 其他类型逻辑...
                    pass

                duration = time.time() - start_time
                await self._mark_status(run_id, task["task_id"], biz_date, "SUCCESS", attempt, duration=duration)
                return
            except Exception as e:
                logger.error(f"[{task['task_id']}] attempt {attempt} failed: {e}")
                if attempt < max_retry:
                    await asyncio.sleep(task.get("retry_interval", 60))
                    continue
                
                await self._mark_status(run_id, task["task_id"], biz_date, "FAILED", attempt, 
                                        error=str(e), stack=traceback.format_exc())
                await alerter.alert("ERROR", f"任务失败: {task['task_id']}", {"biz_date": biz_date.isoformat(), "error": str(e)})
                raise

    async def _run_python_isolated(self, task: dict, biz_date: date, timeout: int):
        """子进程隔离执行, 带内存上限 (E3-S2)"""
        mem_limit = task.get('mem_limit_mb', 1500) * 1024 * 1024
        cmd = [
            "prlimit", f"--as={mem_limit}",
            "--",
            "python3", task["script"],
            "--biz-date", biz_date.isoformat()
        ]
        logger.info(f"执行隔离任务: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            if process.returncode != 0:
                raise Exception(f"Exit code {process.returncode}: {stderr.decode()[:500]}")
            return stdout.decode()
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"任务执行超时 ({timeout}s)")

    async def _run_sql(self, task: dict, biz_date: date, timeout: int):
        # SQL 执行逻辑...
        pass

    async def _mark_status(self, run_id, task_id, biz_date, status, attempt, duration=0, error=None, stack=None):
        sql = """
            INSERT INTO meta_pipeline_run 
            (run_id, pipeline_id, biz_date, task_id, status, retry_count, started_at, duration_sec, error_message, error_stack)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status=VALUES(status),
                retry_count=VALUES(retry_count),
                duration_sec=VALUES(duration_sec),
                error_message=VALUES(error_message),
                error_stack=VALUES(error_stack),
                finished_at=IF(VALUES(status)='SUCCESS' OR VALUES(status)='FAILED', NOW(), finished_at)
        """
        await cloud_db.execute(sql, (run_id, self.pipeline_id, biz_date, task_id, status, attempt, duration, error, stack))
