import logging
import json
import aiomysql
from typing import Optional
from gsd_shared.validation.result import ValidationResult

logger = logging.getLogger(__name__)

class AuditRepository:
    """
    数据校验结果持久化仓储
    
    负责将 ValidationResult 对象保存至云端 MySQL 的 data_audit_summaries 与 data_audit_details 表。
    支持幂等写入 (ON DUPLICATE KEY UPDATE)。
    """
    
    def __init__(self, db_pool: aiomysql.Pool):
        """
        初始化仓储
        
        Args:
            db_pool: aiomysql 连接池
        """
        self.db_pool = db_pool

    async def save_result(self, result: ValidationResult) -> bool:
        """
        保存校验结果 (事务操作)
        
        1. 插入/更新 data_audit_summaries (主表)
        2. 如果是从 FAIL/WARN 转为 PASS，或有更新，重写 details
        3. 删除旧的关联详情 (CASCADE 自动处理困难，需逻辑删除或覆盖)
        * 实际策略: 利用 ON DUPLICATE KEY UPDATE 更新主表，然后先 DELETE 详情再 INSERT 新详情
        
        Args:
            result: 校验结果对象
            
        Returns:
            bool: 是否保存成功
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("BEGIN")
                    
                    try:
                        # 1. Upsert Summary
                        # 如果记录存在 (data_type + target + trade_date 冲突)，更新 level, issue_count, description, updated_at
                        sql_summary = """
                            INSERT INTO data_audit_summaries 
                            (data_type, target, trade_date, level, issue_count, description)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE 
                                level = VALUES(level),
                                issue_count = VALUES(issue_count),
                                description = VALUES(description),
                                updated_at = NOW()
                        """
                        
                        # 自动推断 trade_date: 如果 target 是日期格式，直接使用；否则使用 result.timestamp 的日期
                        # 简单起见，这里假设调用方保证 result.timestamp 是正确的业务时间
                        trade_date = result.timestamp.date()
                        # 特殊情况: 如果 target 是日期字符串 (如 MarketValidator)，那 trade_date 应该就是 target
                        if result.data_type == "market":
                             # 尝试解析 target 作为日期，或者直接信任 timestamp
                             pass 
                        
                        # 构造描述: "Passed" 或 "Failed: xxx"
                        desc = f"{result.level.value}"
                        if not result.is_passed() and result.issues:
                            desc = f"{result.level.value}: {result.issues[0].message[:100]}"
                        
                        await cur.execute(sql_summary, (
                            result.data_type,
                            result.target,
                            trade_date,
                            result.level.value,
                            len(result.issues),
                            desc
                        ))
                        
                        # 获取 ID (可能是新插入的 ID，或者是现有的 ID? ON DUPLICATE 这里 behavior 需要注意)
                        # MySQL 的 lastrowid 在 ON DUPLICATE KEY UPDATE 时，如果更新了，可能返回 ID
                        # 为了稳妥，我们再次查询一次 ID
                        await cur.execute(
                            "SELECT id FROM data_audit_summaries WHERE data_type=%s AND target=%s AND trade_date=%s",
                            (result.data_type, result.target, trade_date)
                        )
                        row = await cur.fetchone()
                        if not row:
                            raise ValueError("Failed to retrieve summary ID after upsert")
                        summary_id = row[0]
                        
                        # 2. Refresh Details
                        # 先删除当天的旧详情 (全量覆盖策略)
                        await cur.execute("DELETE FROM data_audit_details WHERE summary_id = %s", (summary_id,))
                        
                        # 批量插入新详情
                        if result.issues:
                            sql_details = """
                                INSERT INTO data_audit_details
                                (summary_id, dimension, level, message, context)
                                VALUES (%s, %s, %s, %s, %s)
                            """
                            detail_values = []
                            for issue in result.issues:
                                detail_values.append((
                                    summary_id,
                                    issue.dimension,
                                    issue.level.value,
                                    issue.message[:512], # 截断防止溢出
                                    json.dumps(issue.context) if issue.context else None
                                ))
                            
                            await cur.executemany(sql_details, detail_values)
                        
                        await cur.execute("COMMIT")
                        logger.info(f"✅ Saved audit result for {result.data_type}:{result.target} (ID: {summary_id})")
                        return True
                        
                    except Exception as e:
                        await cur.execute("ROLLBACK")
                        logger.error(f"Error saving audit result details: {e}")
                        raise e
                        
        except Exception as e:
            logger.error(f"❌ Failed to persist validation result: {e}")
            return False
