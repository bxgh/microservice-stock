
import json
import datetime
from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("stock-manager.task_command")


class TaskCommandService:
    """任务指令队列服务"""

    @staticmethod
    def _parse_json_field(value: Any) -> Dict[str, Any]:
        """
        解析 JSON 字段
        :param value: 数据库返回的字段值
        :return: 解析后的字典
        """
        if isinstance(value, dict):
            return value
        if value:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse JSON field: {value}")
                return {}
        return {}

    async def create_command(
            self, task_id: str, params: Dict[str, Any]) -> int:
        """
        创建任务指令
        :param task_id: 任务标识符
        :param params: 参数字典
        :return: 指令ID
        """
        try:
            sql = """
                INSERT INTO task_commands (task_id, params, status)
                VALUES (%s, %s, 'PENDING')
            """
            params_json = json.dumps(params)

            await db.execute(sql, (task_id, params_json))

            # 获取刚插入的 ID
            id_res = await db.execute("SELECT LAST_INSERT_ID()")
            command_id = id_res[0][0]

            logger.info(f"Created task command: {task_id}, ID: {command_id}")
            return command_id
        except Exception as e:
            logger.error(f"Failed to create task command: {e}")
            raise e

    async def get_commands(self,
                           task_id: Optional[str] = None,
                           status: Optional[str] = None,
                           limit: int = 20) -> List[Dict[str,
                                                         Any]]:
        """
        查询指令列表
        """
        try:
            sql = "SELECT id, task_id, params, status, created_at, executed_at, result FROM task_commands WHERE 1=1"
            query_params = []

            if task_id:
                sql += " AND task_id = %s"
                query_params.append(task_id)
            if status:
                sql += " AND status = %s"
                query_params.append(status)

            sql += " ORDER BY id DESC LIMIT %s"
            query_params.append(limit)

            rows = await db.execute(sql, tuple(query_params))

            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "task_id": row[1],
                    "params": self._parse_json_field(row[2]),
                    "status": row[3],
                    "created_at": row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else None,
                    "executed_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else None,
                    "result": row[6]
                })
            return results
        except Exception as e:
            logger.error(f"Failed to get task commands: {e}")
            raise e

    async def get_command_by_id(
            self, command_id: int) -> Optional[Dict[str, Any]]:
        """
        查询单个指令详情
        """
        try:
            sql = "SELECT id, task_id, params, status, created_at, executed_at, result FROM task_commands WHERE id = %s"
            rows = await db.execute(sql, (command_id,))
            if not rows:
                return None

            row = rows[0]
            return {
                "id": row[0],
                "task_id": row[1],
                "params": self._parse_json_field(
                    row[2]),
                "status": row[3],
                "created_at": row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else None,
                "executed_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else None,
                "result": row[6]}
        except Exception as e:
            logger.error(f"Failed to get task command {command_id}: {e}")
            raise e
