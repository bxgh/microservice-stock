from typing import Dict, Any, List
from app.utils.http_client import http_client
from app.utils.logger import get_logger

logger = get_logger("stock-manager.scheduler_proxy")

class SchedulerProxyService:
    """调度代理服务"""
    
    async def get_all_jobs(self) -> Dict[str, List[Dict[str, Any]]]:
        """聚合所有容器的调度任务"""
        containers = ["baostock", "akshare", "pywencai"]
        all_jobs = []
        
        for container in containers:
            try:
                result = await http_client.get(container, "/api/v1/scheduler/jobs")
                jobs = result.get("jobs", [])
                all_jobs.extend(jobs)
            except Exception as e:
                logger.warning(f"获取 {container} 任务列表失败: {e}")
        
        return {"jobs": all_jobs}
    
    async def control_job(self, container: str, job_id: str, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """转发任务控制指令"""
        try:
            # V1.2+ 支持带参数运行
            json_body = {}
            if params and action == "run":
                json_body = {"params": params}
                
            result = await http_client.post(
                container,
                f"/api/v1/scheduler/jobs/{job_id}/{action}",
                json=json_body
            )
            return result
        except Exception as e:
            logger.error(f"控制任务 {job_id} 失败: {e}")
            raise
    
    async def get_job_logs(self, container: str, job_id: str, lines: int = 50) -> Dict[str, Any]:
        """代理获取任务日志"""
        try:
            result = await http_client.get(
                container,
                f"/api/v1/scheduler/jobs/{job_id}/logs",
                params={"lines": lines}
            )
            return result
        except Exception as e:
            logger.error(f"获取任务日志失败: {e}")
            raise
