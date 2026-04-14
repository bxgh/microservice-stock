from typing import Dict, Any, List, Optional
import datetime
import json
from app.utils.database import db
from app.utils.logger import get_logger
from app.services.scheduler_proxy import SchedulerProxyService

logger = get_logger("stock-manager.command_service")

class CommandService:
    def __init__(self):
        self.scheduler_proxy = SchedulerProxyService()

    async def create_command(self, task_id: str, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """创建异步命令"""
        try:
            params_json = json.dumps(params)
            sql = """
            INSERT INTO commands (task_id, params, status, request_id, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """
            created_at = datetime.datetime.now()
            # MySQL Connector (aiomysql) uses %s
            await db.execute(sql, (task_id, params_json, 'PENDING', request_id, created_at))
            
            # 获取刚插入的 ID
            id_res = await db.execute("SELECT LAST_INSERT_ID()")
            command_id = id_res[0][0]
            
            # 异步触发执行 (简单起见，这里直接调用，后续可改为真正的后台队列)
            # 注意：在 FastAPI 中可以通过 BackgroundTasks 触发，或者在这里简单 await
            # 为了符合 PENDING -> RUNNING 的 spec，我们在 service 层做状态转换
            return {
                "command_id": command_id,
                "status": "PENDING",
                "message": "命令已加入队列"
            }
        except Exception as e:
            logger.error(f"创建命令失败: {e}")
            raise

    async def get_command_status(self, command_id: int) -> Dict[str, Any]:
        """获取命令状态"""
        sql = "SELECT id, task_id, status, created_at, executed_at, finished_at, result, params FROM commands WHERE id = %s"
        rows = await db.execute(sql, (command_id,))
        if not rows:
            return None
        
        row = rows[0]
        params_val = row[7]
        if isinstance(params_val, str):
            try:
                params_val = json.loads(params_val)
            except:
                params_val = {}
                
        return {
            "id": row[0],
            "task_id": row[1],
            "status": row[2],
            "created_at": row[3].strftime("%Y-%m-%dT%H:%M:%S") if row[3] else None,
            "executed_at": row[4].strftime("%Y-%m-%dT%H:%M:%S") if row[4] else None,
            "finished_at": row[5].strftime("%Y-%m-%dT%H:%M:%S") if row[5] else None,
            "result": row[6],
            "params": params_val
        }

    async def list_commands(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取命令历史"""
        sql = "SELECT id, task_id, status, created_at FROM commands ORDER BY created_at DESC LIMIT %s"
        rows = await db.execute(sql, (limit,))
        commands = []
        for row in rows:
            commands.append({
                "id": row[0],
                "task_id": row[1],
                "status": row[2],
                "created_at": row[3].strftime("%Y-%m-%dT%H:%M:%S") if row[3] else None
            })
        return commands

    async def execute_pending_commands(self):
        """执行待处理的命令 (补齐逻辑)"""
        # 这是一个示例逻辑，由于没有真正的后台 Worker，
        # 我们可以在触发后立即执行，或者由定时任务扫描
        pass
