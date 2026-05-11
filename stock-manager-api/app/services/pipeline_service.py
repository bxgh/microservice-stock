
import json
from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("stock-manager.pipeline_service")

class PipelineService:
    """任务流水线状态服务"""

    @staticmethod
    def _parse_json_field(value: Any) -> Dict[str, Any]:
        """解析 JSON 字段"""
        if isinstance(value, dict):
            return value
        if value:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    async def get_pipeline_runs(
        self,
        pipeline_id: Optional[str] = None,
        biz_date: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        查询流水线运行记录
        """
        try:
            sql = """
                SELECT 
                    run_id, pipeline_id, biz_date, task_id, status, 
                    started_at, finished_at, duration_sec, retry_count, 
                    max_retry, error_message, error_stack, output_summary
                FROM meta_pipeline_run 
                WHERE is_deleted = 0
            """
            params = []
            if pipeline_id:
                sql += " AND pipeline_id = %s"
                params.append(pipeline_id)
            if biz_date:
                sql += " AND biz_date = %s"
                params.append(biz_date)
            if status:
                sql += " AND status = %s"
                params.append(status)
            
            sql += " ORDER BY started_at DESC LIMIT %s"
            params.append(limit)

            rows = await db.execute(sql, tuple(params))
            
            results = []
            for row in rows:
                results.append({
                    "run_id": row[0],
                    "pipeline_id": row[1],
                    "biz_date": row[2].isoformat() if row[2] else None,
                    "task_id": row[3],
                    "status": row[4],
                    "started_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else None,
                    "finished_at": row[6].strftime("%Y-%m-%d %H:%M:%S") if row[6] else None,
                    "duration_sec": row[7],
                    "retry_count": row[8],
                    "max_retry": row[9],
                    "error_message": row[10],
                    "error_stack": row[11],
                    "output_summary": self._parse_json_field(row[12])
                })
            return results
        except Exception as e:
            logger.error(f"Failed to get pipeline runs: {e}")
            raise e

    async def get_daily_stats(self, biz_date: str) -> Dict[str, Any]:
        """
        获取指定日期的任务统计简报
        """
        try:
            sql = """
                SELECT status, COUNT(*) 
                FROM meta_pipeline_run 
                WHERE biz_date = %s
                GROUP BY status
            """
            rows = await db.execute(sql, (biz_date,))
            
            stats = {
                "biz_date": biz_date,
                "total": 0,
                "SUCCESS": 0,
                "FAILED": 0,
                "RUNNING": 0,
                "PENDING": 0,
                "SKIPPED": 0
            }
            
            for row in rows:
                status = row[0]
                count = row[1]
                if status in stats:
                    stats[status] = count
                stats["total"] += count
                
            return stats
        except Exception as e:
            logger.error(f"Failed to get daily stats for {biz_date}: {e}")
            raise e

    async def create_run(self, pipeline_id: str, biz_date: str, task_id: str) -> str:
        """创建任务运行记录"""
        import time
        run_id = f"run_{int(time.time())}_{task_id}"
        try:
            sql = """
                INSERT INTO meta_pipeline_run (run_id, pipeline_id, biz_date, task_id, status, started_at)
                VALUES (%s, %s, %s, %s, 'RUNNING', NOW())
            """
            await db.execute(sql, (run_id, pipeline_id, biz_date, task_id))
            return run_id
        except Exception as e:
            logger.error(f"Failed to create pipeline run: {e}")
            raise e

    async def update_run(self, run_id: str, status: str, error_msg: Optional[str] = None, output_summary: Optional[Dict[str, Any]] = None):
        """更新任务运行记录"""
        try:
            sql = """
                UPDATE meta_pipeline_run 
                SET status = %s, finished_at = NOW(), 
                    duration_sec = TIMESTAMPDIFF(SECOND, started_at, NOW()),
                    error_message = %s, output_summary = %s
                WHERE run_id = %s
            """
            output_json = json.dumps(output_summary) if output_summary else None
            await db.execute(sql, (status, error_msg, output_json, run_id))
        except Exception as e:
            logger.error(f"Failed to update pipeline run {run_id}: {e}")
            raise e

    async def is_stage_success(self, pipeline_id: str, biz_date: str, task_id: str) -> bool:
        """检查特定阶段是否已成功执行"""
        try:
            sql = """
                SELECT COUNT(*) FROM meta_pipeline_run 
                WHERE pipeline_id = %s AND biz_date = %s AND task_id = %s AND status = 'SUCCESS'
                AND is_deleted = 0
            """
            rows = await db.execute(sql, (pipeline_id, biz_date, task_id))
            return rows[0][0] > 0
        except Exception as e:
            logger.error(f"Failed to check stage success: {e}")
            return False

pipeline_service = PipelineService()
