from typing import List, Optional, Dict, Any
from app.utils.database import db
from app.utils.logger import get_logger
from app.models.data_audit import DataAuditSummary, DataAuditDetail
import json

logger = get_logger("stock-manager.data_audit")


class DataAuditService:
    """数据审计日志服务"""

    async def get_summaries(self,
                            page: int = 1,
                            size: int = 20,
                            trade_date: Optional[str] = None,
                            data_type: Optional[str] = None,
                            level: Optional[str] = None) -> Dict[str, Any]:
        """查询审计汇总记录"""
        try:
            offset = (page - 1) * size
            params = []
            where_clauses = ["1=1"]

            if trade_date:
                where_clauses.append("trade_date = %s")
                params.append(trade_date)
            if data_type:
                where_clauses.append("data_type = %s")
                params.append(data_type)
            if level:
                where_clauses.append("level = %s")
                params.append(level)

            where_sql = " AND ".join(where_clauses)

            # Count
            count_sql = f"SELECT COUNT(*) FROM data_audit_summaries WHERE {where_sql}"
            count_res = await db.execute(count_sql, tuple(params))
            total = count_res[0][0]

            # Query
            query_sql = f"""
                SELECT id, data_type, target, trade_date, level, issue_count, description, created_at, updated_at
                FROM data_audit_summaries
                WHERE {where_sql}
                ORDER BY trade_date DESC, id DESC
                LIMIT %s OFFSET %s
            """
            params.extend([size, offset])
            rows = await db.execute(query_sql, tuple(params))

            items = []
            for row in rows:
                items.append(DataAuditSummary(
                    id=row[0],
                    data_type=row[1],
                    target=row[2],
                    trade_date=row[3],
                    level=row[4],
                    issue_count=row[5],
                    description=row[6],
                    created_at=row[7],
                    updated_at=row[8]
                ))

            return {
                "items": items,
                "total": total,
                "page": page,
                "size": size
            }
        except Exception as e:
            logger.error(f"Failed to get audit summaries: {e}")
            raise e

    async def get_summary_by_id(self, id: int) -> Optional[DataAuditSummary]:
        """获取单个汇总详情"""
        try:
            sql = "SELECT id, data_type, target, trade_date, level, issue_count, description, created_at, updated_at FROM data_audit_summaries WHERE id = %s"
            rows = await db.execute(sql, (id,))
            if not rows:
                return None
            row = rows[0]
            return DataAuditSummary(
                id=row[0],
                data_type=row[1],
                target=row[2],
                trade_date=row[3],
                level=row[4],
                issue_count=row[5],
                description=row[6],
                created_at=row[7],
                updated_at=row[8]
            )
        except Exception as e:
            logger.error(f"Failed to get audit summary {id}: {e}")
            raise e

    async def get_details(self, summary_id: int) -> List[DataAuditDetail]:
        """获取某次审计的详细记录"""
        try:
            sql = """
                SELECT id, summary_id, dimension, level, message, context, created_at
                FROM data_audit_details
                WHERE summary_id = %s
                ORDER BY id ASC
            """
            rows = await db.execute(sql, (summary_id,))

            items = []
            for row in rows:
                context_val = row[5]
                if isinstance(context_val, str):
                    try:
                        context_val = json.loads(context_val)
                    except BaseException:
                        context_val = {}
                elif context_val is None:
                    context_val = {}

                items.append(DataAuditDetail(
                    id=row[0],
                    summary_id=row[1],
                    dimension=row[2],
                    level=row[3],
                    message=row[4],
                    context=context_val,
                    created_at=row[6]
                ))
            return items
        except Exception as e:
            logger.error(
                f"Failed to get audit details for summary {summary_id}: {e}")
            raise e


data_audit_service = DataAuditService()
