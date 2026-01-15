
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.services.task_command_service import TaskCommandService

router = APIRouter()
service = TaskCommandService()

class CommandCreateRequest(BaseModel):
    task_id: str
    params: Dict[str, Any]

@router.post("", summary="下达任务指令")
async def create_task_command(request: CommandCreateRequest = Body(...)):
    """
    下达新的任务指令到队列中
    """
    try:
        command_id = await service.create_command(request.task_id, request.params)
        return {
            "id": command_id,
            "status": "PENDING",
            "message": "指令已成功入队"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", summary="获取指令列表")
async def list_task_commands(
    task_id: Optional[str] = Query(None, description="过滤任务ID"),
    status: Optional[str] = Query(None, description="过滤状态"),
    limit: int = Query(20, description="返回记录条数")
):
    """
    获取任务指令队列的历史记录，支持按任务ID和状态过滤
    """
    try:
        commands = await service.get_commands(task_id, status, limit)
        return {"commands": commands}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{command_id}", summary="查看指令状态")
async def get_task_command(command_id: int):
    """
    根据ID查看特定指令的执行状态和结果
    """
    try:
        command = await service.get_command_by_id(command_id)
        if not command:
            raise HTTPException(status_code=404, detail="指令不存在")
        return command
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
