
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks
from pydantic import BaseModel

from app.utils.logger import get_logger
from app.services.collection_service import CollectionService

router = APIRouter()
logger = get_logger("baostock-api.api.collect")

# --- Pydantic Models ---

class StockHistoryCollectRequest(BaseModel):
    stock_code: str
    start_date: str = "1990-01-01"
    end_date: str = "" # Default to now
    clear_existing: bool = False
    callback_url: Optional[str] = None

class BatchCollectRequest(BaseModel):
    stock_codes: List[str]
    start_date: str = "2024-01-01"

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    stock_code: Optional[str] = None
    records_collected: Optional[int] = None
    error: Optional[str] = None

# --- Endpoints ---

@router.post("/collect/stock_history", status_code=202)
async def collect_stock_history(
    request: Request,
    payload: StockHistoryCollectRequest,
    background_tasks: BackgroundTasks
):
    """
    [异步] 触发个股历史数据重新采集/修复
    """
    # 1. 获取 Service 实例 (懒加载或从 app.state 获取)
    service: CollectionService = getattr(request.app.state, "collection_service", None)
    if not service:
        raise HTTPException(status_code=500, detail="CollectionService not initialized")
        
    # 2. 提交任务
    task_id = await service.submit_collection_task(
        stock_code=payload.stock_code,
        start_date=payload.start_date,
        clear_existing=payload.clear_existing,
        callback_url=payload.callback_url
    )
    
    # 3. 添加后台任务
    background_tasks.add_task(
        service.run_stock_history_collection,
        task_id=task_id,
        stock_code=payload.stock_code,
        start_date=payload.start_date,
        clear_existing=payload.clear_existing,
        callback_url=payload.callback_url
    )
    
    return {
        "status": "accepted",
        "task_id": task_id,
        "message": "采集任务已启动",
    }

@router.get("/collect/task/{task_id}", response_model=TaskStatusResponse)
async def get_collection_task_status(request: Request, task_id: str):
    """
    查询采集任务状态
    """
    service: CollectionService = getattr(request.app.state, "collection_service", None)
    if not service:
        raise HTTPException(status_code=500, detail="CollectionService not initialized")
        
    task_data = service.get_task_status(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # 转换格式
    meta = task_data.get("metadata", {})
    result = task_data.get("result") or {}
    
    return TaskStatusResponse(
        task_id=task_data["id"],
        status=task_data["status"],
        progress=task_data.get("progress", 0),
        stock_code=meta.get("stock_code"),
        records_collected=result.get("records_collected"),
        error=task_data.get("error")
    )

@router.post("/collect/batch", status_code=501)
async def batch_collect(payload: BatchCollectRequest):
    """
    [P2] 批量采集 (尚未实现)
    """
    return {"message": "Not implemented yet"}
