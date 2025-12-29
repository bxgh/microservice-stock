"""
任务执行日志 API

提供查询历史任务执行记录的接口
"""
from fastapi import APIRouter, Query, Request
from app.services.execution_logs import get_execution_logs

router = APIRouter()

@router.get("/logs/execution")
async def list_execution_logs(
    request: Request,
    limit: int = Query(50, description="返回记录数", ge=1, le=500),
    task_name: str = Query(None, description="过滤特定任务名称")
):
    """
    获取任务执行历史日志
    
    ---
    参数:
    - limit: 返回的记录数量（默认50，最多500）
    - task_name: 可选，过滤特定任务（如 "kline_daily_sync"）
    
    返回示例:
    ```json
    {
      "logs": [
        {
          "id": 8,
          "task_name": "kline_daily_sync",
          "execution_time": "2025-12-26 19:00:00",
          "status": "SUCCESS",
          "records_processed": 5465,
          "details": "智能增量同步完成：5,465 条记录",
          "duration_seconds": 10.465
        }
      ],
      "total": 1
    }
    ```
    """
    return await get_execution_logs(limit=limit, task_name=task_name)
