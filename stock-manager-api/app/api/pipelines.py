
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from app.services.pipeline_service import pipeline_service

router = APIRouter()

@router.get("/runs", summary="查询流水线运行记录")
async def list_pipeline_runs(
    pipeline_id: Optional[str] = Query(None, description="流水线ID"),
    biz_date: Optional[str] = Query(None, description="业务日期 (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="任务状态"),
    limit: int = Query(50, description="返回记录条数")
):
    """
    获取任务状态机 (meta_pipeline_run) 的运行记录，支持多维度过滤。
    """
    try:
        runs = await pipeline_service.get_pipeline_runs(
            pipeline_id=pipeline_id,
            biz_date=biz_date,
            status=status,
            limit=limit
        )
        return {"runs": runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", summary="获取每日统计简报")
async def get_pipeline_stats(
    biz_date: str = Query(..., description="业务日期 (YYYY-MM-DD)")
):
    """
    获取指定日期所有流水线任务的执行统计（总数、成功、失败等）。
    """
    try:
        stats = await pipeline_service.get_daily_stats(biz_date)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/runs", summary="手动触发流水线阶段")
async def trigger_pipeline_stage(
    stage_name: str = Query(..., description="阶段名称 (STAGE_A/B/C/D)"),
    biz_date: str = Query(..., description="业务日期 (YYYY-MM-DD)")
):
    """
    手动触发指定的流水线阶段。
    """
    try:
        from app.services.workflow_service import workflow_service
        from datetime import datetime
        dt = datetime.strptime(biz_date, "%Y-%m-%d")
        
        # 异步执行
        import asyncio
        asyncio.create_task(workflow_service.execute_stage(stage_name, dt))
        
        return {"message": f"阶段 {stage_name} 已在后台启动", "biz_date": biz_date}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
