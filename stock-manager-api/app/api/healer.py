from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Dict, Any
from app.services.healer_service import healer_service
from app.utils.logger import get_logger

logger = get_logger("stock-manager.api.healer")
router = APIRouter(prefix="/healer", tags=["Healer"])

@router.post("/repair")
async def trigger_repair(
    limit: int = Query(10, ge=1, le=100),
    background_tasks: BackgroundTasks = None
):
    """
    触发自动修复扫描
    
    - 扫描 dq_findings 中的 ERROR 记录并执行仲裁修复
    """
    if background_tasks:
        background_tasks.add_task(healer_service.scan_and_repair, limit)
        return {"status": "accepted", "message": f"正在后台处理最多 {limit} 条异常记录"}
    else:
        results = await healer_service.scan_and_repair(limit)
        return {"status": "completed", "results": results}

@router.post("/repair/{finding_id}")
async def repair_single(finding_id: int):
    """手动触发单条异常修复"""
    success = await healer_service.repair_finding(finding_id)
    if success:
        return {"status": "success", "message": f"异常 {finding_id} 已修复"}
    else:
        raise HTTPException(status_code=500, detail=f"修复异常 {finding_id} 失败，请检查日志")

@router.post("/rollback/{repair_id}")
async def rollback_repair(repair_id: int):
    """执行一键回滚"""
    success = await healer_service.rollback_repair(repair_id)
    if success:
        return {"status": "success", "message": f"修复记录 {repair_id} 已成功回滚"}
    else:
        raise HTTPException(status_code=400, detail=f"回滚失败，记录不存在或状态不正确")

@router.get("/logs")
async def get_repair_logs(limit: int = 20):
    """获取修复日志"""
    from app.utils.database import db
    sql = "SELECT * FROM meta_repair_log ORDER BY created_at DESC LIMIT %s"
    logs = await db.execute(sql, (limit,))
    return {"logs": logs}
