from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Query
from typing import Dict, Any, List
from app.services.command_service import CommandService
from app.services.scheduler_proxy import SchedulerProxyService

router = APIRouter()
command_service = CommandService()
scheduler_proxy = SchedulerProxyService()

@router.post("")
async def trigger_command(
    request: Request,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """手动触发任务命令"""
    task_id = payload.get("task_id")
    params = payload.get("params", {})
    request_id = getattr(request.state, "request_id", "unknown")
    
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")
    
    # 1. 创建命令记录
    result = await command_service.create_command(task_id, params, request_id)
    command_id = result["command_id"]
    
    # 2. 加入后台任务执行
    background_tasks.add_task(run_command_background, command_id)
    
    return result

@router.get("/{command_id}")
async def get_command_status(command_id: int):
    """查询命令具体状态"""
    status = await command_service.get_command_status(command_id)
    if not status:
        raise HTTPException(status_code=404, detail="Command not found")
    return status

@router.get("")
async def list_commands(limit: int = Query(20, ge=1, le=100)):
    """获取命令历史记录"""
    commands = await command_service.list_commands(limit)
    return {"commands": commands}

async def run_command_background(command_id: int):
    """后台执行命令的辅助函数"""
    from app.utils.database import db
    from app.utils.logger import get_logger
    import datetime
    
    logger = get_logger("stock-manager.command_executor")
    
    # 获取任务详情
    status_info = await command_service.get_command_status(command_id)
    if not status_info:
        return
    
    task_id = status_info["task_id"]
    params = status_info.get("params", {})
    
    # 更新状态为 RUNNING
    await db.execute(
        "UPDATE commands SET status = 'RUNNING', executed_at = %s WHERE id = %s",
        (datetime.datetime.now(), command_id)
    )
    
    try:
        # 执行根据 task_id 映射具体逻辑
        # 目前主要通过 scheduler_proxy 触发远程任务
        # 容器映射逻辑 (仅示例)
        container_map = {
            "daily_kline_sync": "baostock",
            "sync_tick": "baostock", # 假设在 baostock 容器
            "pre_market_gate": "akshare"
        }
        container = container_map.get(task_id, "baostock")
        
        # 3. 参数模板替换
        final_params = params.copy()
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        for k, v in final_params.items():
            if isinstance(v, str) and "{{target_date}}" in v:
                final_params[k] = v.replace("{{target_date}}", today_str)
                logger.info(f"Param template substituted: {k} -> {final_params[k]}")

        # 触发远程任务的 'run' 操作
        # 注意: 远程任务的 job_id 必须与传入的 task_id 匹配，或者进行转换
        # 支持传递参数 (V1.2+)
        res = await scheduler_proxy.control_job(container, task_id, "run", params=final_params)
        
        # 更新状态为 DONE
        await db.execute(
            "UPDATE commands SET status = 'DONE', finished_at = %s, result = %s WHERE id = %s",
            (datetime.datetime.now(), str(res), command_id)
        )
        logger.info(f"Command {command_id} ({task_id}) executed successfully")
    except Exception as e:
        logger.error(f"Command {command_id} failed: {e}")
        # 更新状态为 FAILED
        await db.execute(
            "UPDATE commands SET status = 'FAILED', finished_at = %s, result = %s WHERE id = %s",
            (datetime.datetime.now(), f"Error: {str(e)}", command_id)
        )
