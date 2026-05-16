import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# 确保可以导入 shared 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
load_dotenv("/home/ubuntu/microservice-stock/.env")

# 适配 DBManager 环境变量
os.environ["MYSQL_HOST"] = os.getenv("DB_HOST", "localhost")
os.environ["MYSQL_PORT"] = os.getenv("DB_PORT", "3306")
os.environ["MYSQL_USER"] = os.getenv("DB_USER", "root")
os.environ["MYSQL_PASSWORD"] = os.getenv("DB_PASSWORD", "")
os.environ["MYSQL_DB"] = os.getenv("DB_NAME", "stock")

from shared.db.connection import DBManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("PhysicalAuditor")

class InternalConsistencyChecker:
    def __init__(self):
        self.pool = None

    async def run_audit(self, limit_days: int = 30):
        """执行物理红线审计 (默认扫描最近 30 天)"""
        if not self.pool:
            self.pool = await DBManager.get_pool()
            
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                logger.info(f"开始物理红线审计 (扫描近 {limit_days} 天数据)...")
                
                # 1. 价格逻辑序异常: low 必须是最小值，high 必须是最大值
                sql_order = """
                SELECT ts_code, trade_date, open, high, low, close 
                FROM stock_kline_daily 
                WHERE (low > open OR low > close OR high < open OR high < close OR low > high)
                  AND trade_date > DATE_SUB(CURDATE(), INTERVAL %s DAY)
                """
                await cur.execute(sql_order, (limit_days,))
                order_errors = await cur.fetchall()
                
                # 2. 零值/异常值审计
                sql_zero = """
                SELECT ts_code, trade_date 
                FROM stock_kline_daily 
                WHERE (open <= 0 OR high <= 0 OR low <= 0 OR close <= 0)
                  AND trade_date > DATE_SUB(CURDATE(), INTERVAL %s DAY)
                """
                await cur.execute(sql_zero, (limit_days,))
                zero_errors = await cur.fetchall()

                # 3. 统计并处理
                total_errors = len(order_errors) + len(zero_errors)
                logger.info(f"审计结束. 逻辑序错误: {len(order_errors)}, 零值错误: {len(zero_errors)}")
                
                if total_errors > 0:
                    # 将异常写入任务队列进行重采修复
                    sql_task = """
                    INSERT IGNORE INTO meta_task_queue (task_type, ts_code, trade_date, error_type, status)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    tasks = []
                    for r in order_errors:
                        tasks.append(('kline_audit_repair', r[0], r[1], 'PHYSICAL_ERROR', 'PENDING'))
                    for r in zero_errors:
                        tasks.append(('kline_audit_repair', r[0], r[1], 'PHYSICAL_ERROR', 'PENDING'))
                    
                    await cur.executemany(sql_task, tasks)
                    logger.warning(f"已将 {len(tasks)} 条物理异常记录注入修复队列")
                else:
                    logger.info("✅ 未发现物理红线异常")

if __name__ == "__main__":
    checker = InternalConsistencyChecker()
    asyncio.run(checker.run_audit(limit_days=365)) # 扩大扫描范围至 1 年
