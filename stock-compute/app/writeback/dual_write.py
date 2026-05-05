from datetime import date
from app.utils.logger import get_logger
from app.utils.database import cloud_db, internal_db
from app.utils.alerter import alerter

logger = get_logger("stock-compute.writeback")

class DualWriter:
    """计算结果双写: 内网副本 + 云端 MySQL (E4-S3)"""

    async def writeback(self, biz_date: date, table: str, records: list, producer_task: str):
        if not records:
            return

        # 1. 写入内网副本 (本地事务, 极快)
        try:
            await internal_db.execute(f"DELETE FROM {table} WHERE biz_date=%s", (biz_date,))
            await internal_db.batch_insert(table, records)
            logger.info(f"[local] 已回写 {table}: {len(records)} 条")
        except Exception as e:
            logger.error(f"内网回写失败 {table}: {e}")
            await alerter.alert("ERROR", f"内网回写失败 {table}", {"error": str(e)})

        # 2. 写入云端 (通过 SSH 隧道, 可能慢/中断)
        try:
            await cloud_db.execute(f"DELETE FROM {table} WHERE biz_date=%s", (biz_date,))
            await cloud_db.batch_insert(table, records)
            
            # 更新云端就绪状态 (E2-S3)
            await self._update_cloud_readiness(biz_date, table, len(records), producer_task)
            logger.info(f"[cloud] 已回写 {table}: {len(records)} 条")
        except Exception as e:
            logger.error(f"云端回写失败 {table}: {e}")
            # 云端失败不应中断管线，但需触发高等级告警并记入补偿队列
            await alerter.alert("ERROR", f"云端回写失败 {table}", {"error": str(e)})
            # TODO: 实现补偿队列

    async def _update_cloud_readiness(self, biz_date, table, count, task_id):
        sql = """
            INSERT INTO meta_data_readiness 
            (table_name, biz_date, storage, record_count, producer_node, producer_task, ready_at, status)
            VALUES (%s, %s, 'cloud_mysql', %s, 'internal', %s, NOW(), 'READY')
            ON DUPLICATE KEY UPDATE
                record_count=VALUES(record_count),
                producer_task=VALUES(producer_task),
                ready_at=VALUES(ready_at),
                status='READY'
        """
        await cloud_db.execute(sql, (table, biz_date, count, task_id))
