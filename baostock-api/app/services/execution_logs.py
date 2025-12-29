import asyncio
from app.utils.database import db

async def get_execution_logs(limit: int = 50, task_name: str = None):
    """获取任务执行历史日志
    
    Args:
        limit: 返回的记录数量
        task_name: 可选，过滤特定任务名称
    
    Returns:
        包含执行日志的字典列表
    """
    try:
        if task_name:
            sql = """
                SELECT id, task_name, execution_time, status, records_processed, 
                       details, duration_seconds
                FROM sync_execution_logs 
                WHERE task_name = %s
                ORDER BY execution_time DESC 
                LIMIT %s
            """
            rows = await db.execute(sql, (task_name, limit))
        else:
            sql = """
                SELECT id, task_name, execution_time, status, records_processed, 
                       details, duration_seconds
                FROM sync_execution_logs 
                ORDER BY execution_time DESC 
                LIMIT %s
            """
            rows = await db.execute(sql, (limit,))
        
        logs = []
        for row in rows:
            logs.append({
                "id": row[0],
                "task_name": row[1],
                "execution_time": row[2].strftime("%Y-%m-%d %H:%M:%S") if row[2] else None,
                "status": row[3],
                "records_processed": row[4],
                "details": row[5],
                "duration_seconds": float(row[6]) if row[6] else 0
            })
        
        return {"logs": logs, "total": len(logs)}
    
    except Exception as e:
        from app.utils.logger import get_logger
        logger = get_logger("execution_logs")
        logger.error(f"查询执行日志失败: {e}")
        return {"logs": [], "total": 0, "error": str(e)}
