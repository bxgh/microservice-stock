from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import date
from app.models.dq import DQFinding, DQReportSummary
from app.utils.database import db

router = APIRouter()

@router.get("/report/summary", response_model=List[DQReportSummary])
async def get_dq_summary(start_date: date = Query(...), end_date: date = Query(...)):
    """获取数据质量概览报告"""
    sql = """
        SELECT 
            trade_date as check_date,
            COUNT(*) as total_issues,
            SUM(CASE WHEN severity = 'ERROR' THEN 1 ELSE 0 END) as error_count,
            SUM(CASE WHEN severity = 'WARN' THEN 1 ELSE 0 END) as warn_count
        FROM dq_findings
        WHERE trade_date BETWEEN %s AND %s
        GROUP BY trade_date
        ORDER BY trade_date DESC
    """
    rows = await db.execute(sql, (start_date, end_date))
    
    results = []
    for row in rows:
        results.append(DQReportSummary(
            check_date=row[0],
            total_scanned=0, # 暂时不统计总扫描数，需要额外记录
            total_issues=row[1],
            severity_dist={"ERROR": int(row[2]), "WARN": int(row[3])},
            check_type_dist={} # 暂时省略分类统计
        ))
    return results

@router.get("/findings", response_model=List[DQFinding])
async def get_dq_findings(
    ts_code: Optional[str] = None,
    trade_date: Optional[date] = None,
    check_type: Optional[str] = None,
    status: int = 0,
    limit: int = 100
):
    """获取具体的数据质量异常项"""
    sql = "SELECT id, ts_code, trade_date, check_type, severity, finding_msg, diff_data, status, created_at, updated_at FROM dq_findings WHERE 1=1"
    params = []
    
    if ts_code:
        sql += " AND ts_code = %s"
        params.append(ts_code)
    if trade_date:
        sql += " AND trade_date = %s"
        params.append(trade_date)
    if check_type:
        sql += " AND check_type = %s"
        params.append(check_type)
    
    sql += f" AND status = %s ORDER BY created_at DESC LIMIT {limit}"
    params.append(status)
    
    rows = await db.execute(sql, params)
    
    results = []
    for row in rows:
        results.append(DQFinding(
            id=row[0],
            ts_code=row[1],
            trade_date=row[2],
            check_type=row[3],
            severity=row[4],
            finding_msg=row[5],
            diff_data=row[6],
            status=row[7],
            created_at=row[8],
            updated_at=row[9]
        ))
    return results

@router.post("/findings/{finding_id}/resolve")
async def resolve_finding(finding_id: int, status: int = 2):
    """标记问题为已修复或忽略"""
    sql = "UPDATE dq_findings SET status = %s WHERE id = %s"
    await db.execute(sql, (status, finding_id))
    return {"success": True}

@router.post("/task/run-cross-compare")
async def run_cross_compare_task(target_date: Optional[date] = None):
    """手动触发跨源比对任务"""
    from app.services.cross_compare_service import cross_compare_service
    # 异步执行，不等待结束 (Fire and forget)
    import asyncio
    asyncio.create_task(cross_compare_service.run_daily_comparison(target_date))
    return {"message": "跨源比对任务已在后台启动"}
