from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import date
from app.models.dq import DQFinding, DQReportSummary, DQMetricsReport, DQMetricItem
from app.utils.database import db

router = APIRouter()


@router.get("/report/summary", response_model=List[DQReportSummary])
async def get_dq_summary(
        start_date: date = Query(...),
        end_date: date = Query(...)):
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
            total_scanned=0,
            total_issues=row[1],
            severity_dist={"ERROR": int(row[2]), "WARN": int(row[3])},
            check_type_dist={}
        ))
    return results


@router.get("/metrics/history", response_model=List[DQMetricsReport])
async def get_dq_metrics_history(days: int = 30):
    """获取 DQ 指标历史趋势"""
    sql = """
        SELECT trade_date, indicator_name, indicator_value, target_value, status
        FROM dq_metrics_history
        WHERE trade_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY trade_date DESC, indicator_name ASC
    """
    rows = await db.execute(sql, (days,))

    by_date = {}
    for row in rows:
        d = row[0]
        if d not in by_date:
            by_date[d] = []
        by_date[d].append(DQMetricItem(
            indicator_name=row[1],
            indicator_value=row[2],
            target_value=row[3] or 1.0,
            status=row[4]
        ))

    results = []
    for d, metrics in by_date.items():
        results.append(DQMetricsReport(trade_date=d, metrics=metrics))

    return results


@router.get("/findings", response_model=List[DQFinding])
async def get_dq_findings(
    ts_code: Optional[str] = None,
    trade_date: Optional[date] = None,
    rule_id: Optional[str] = None,
    status: str = 'OPEN',
    limit: int = 100
):
    """获取具体的数据质量异常项"""
    sql = "SELECT id, ts_code, trade_date, rule_id, severity, description, diff_data, status, created_at, updated_at FROM dq_findings WHERE 1=1"
    params = []

    if ts_code:
        sql += " AND ts_code = %s"
        params.append(ts_code)
    if trade_date:
        sql += " AND trade_date = %s"
        params.append(trade_date)
    if rule_id:
        sql += " AND rule_id = %s"
        params.append(rule_id)

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
            status=0 if row[7] == 'OPEN' else 1,
            created_at=row[8],
            updated_at=row[9]
        ))
    return results


@router.post("/findings/{finding_id}/resolve")
async def resolve_finding(finding_id: int, status: str = 'RESOLVED'):
    """标记问题为已修复或忽略"""
    sql = "UPDATE dq_findings SET status = %s WHERE id = %s"
    await db.execute(sql, (status, finding_id))
    return {"success": True}


@router.post("/task/run-cross-compare")
async def run_cross_compare_task(target_date: Optional[date] = None):
    """手动触发跨源比对任务"""
    from app.services.cross_compare_service import cross_compare_service
    import asyncio
    asyncio.create_task(
        cross_compare_service.run_daily_comparison(target_date))
    return {"message": "跨源比对任务已在后台启动"}


@router.post("/task/run-business-rules")
async def run_business_rules_task(target_date: Optional[date] = None):
    """手动触发业务规则校验"""
    from app.services.business_rule_validator import business_rule_validator
    if not target_date:
        sql = "SELECT MAX(trade_date) FROM stock_kline_daily"
        res = await db.execute(sql)
        target_date = res[0][0] if res else date.today()

    date_str = target_date.strftime(
        "%Y-%m-%d") if hasattr(target_date, "strftime") else str(target_date)
    import asyncio
    asyncio.create_task(business_rule_validator.validate_price_limit(date_str))
    return {"message": f"日期 {date_str} 的业务规则校验任务已启动"}


@router.post("/task/run-dq-metrics")
async def run_dq_metrics_task(target_date: Optional[date] = None):
    """手动触发 DQ 指标计算"""
    from app.services.dq_metrics_service import dq_metrics_service
    if not target_date:
        sql = "SELECT cal_date FROM trade_cal WHERE cal_date < CURDATE() AND is_open = 1 ORDER BY cal_date DESC LIMIT 1"
        res = await db.execute(sql)
        target_date = res[0][0] if res else date.today()

    date_str = target_date.strftime(
        "%Y-%m-%d") if hasattr(target_date, "strftime") else str(target_date)
    await dq_metrics_service.calculate_daily_metrics(date_str)
    return {"message": f"日期 {date_str} 的 DQ 指标计算完成"}
