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
        """执行物理红线审计与外键/关系对账 (默认扫描最近 30 天)"""
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

                # 3. [E13-S5-T3] daily_basic 与 stock_kline_daily 价格不一致审计
                sql_basic_price_diff = """
                SELECT k.ts_code, k.trade_date, k.close AS k_close, b.close AS b_close
                FROM stock_kline_daily k
                JOIN daily_basic b ON k.ts_code = b.ts_code AND k.trade_date = b.trade_date
                WHERE ABS(k.close - b.close) > 0.01
                  AND k.trade_date > DATE_SUB(CURDATE(), INTERVAL %s DAY)
                """
                await cur.execute(sql_basic_price_diff, (limit_days,))
                price_diff_errors = await cur.fetchall()

                # 4. [E13-S5-T3] daily_basic 估值指标异常审计 (换手率/市值等为负数或市值非正)
                sql_basic_anomaly = """
                SELECT ts_code, trade_date, turnover_rate, volume_ratio, total_share, total_mv
                FROM daily_basic
                WHERE (turnover_rate < 0 OR volume_ratio < 0 OR total_share <= 0 OR total_mv <= 0)
                  AND trade_date > DATE_SUB(CURDATE(), INTERVAL %s DAY)
                """
                await cur.execute(sql_basic_anomaly, (limit_days,))
                basic_anomaly_errors = await cur.fetchall()

                # 5. [E13-S5-T3] 外键一致性审计 - 有K线无估值指标 (剔除停牌/未交易的股票，要求 volume > 0)
                sql_missing_basic = """
                SELECT k.ts_code, k.trade_date
                FROM stock_kline_daily k
                LEFT JOIN daily_basic b ON k.ts_code = b.ts_code AND k.trade_date = b.trade_date
                WHERE b.ts_code IS NULL
                  AND k.volume > 0
                  AND k.trade_date > DATE_SUB(CURDATE(), INTERVAL %s DAY)
                """
                await cur.execute(sql_missing_basic, (limit_days,))
                missing_basic_errors = await cur.fetchall()

                # 6. [E13-S5-T3] 外键一致性审计 - 有估值指标无K线
                sql_missing_kline = """
                SELECT b.ts_code, b.trade_date
                FROM daily_basic b
                LEFT JOIN stock_kline_daily k ON b.ts_code = k.ts_code AND b.trade_date = k.trade_date
                WHERE k.ts_code IS NULL
                  AND b.trade_date > DATE_SUB(CURDATE(), INTERVAL %s DAY)
                """
                await cur.execute(sql_missing_kline, (limit_days,))
                missing_kline_errors = await cur.fetchall()

                # 统计结果
                total_kline_errors = len(order_errors) + len(zero_errors)
                total_basic_errors = len(price_diff_errors) + len(basic_anomaly_errors) + len(missing_basic_errors) + len(missing_kline_errors)
                
                logger.info(f"审计结束.")
                logger.info(f"  [K线物理异常] 逻辑序错误: {len(order_errors)}, 零值错误: {len(zero_errors)}")
                logger.info(f"  [估值物理与关系对账异常] 价格差异错误: {len(price_diff_errors)}, 指标逻辑错误: {len(basic_anomaly_errors)}")
                logger.info(f"  [外键完整性异常] 有K线无估值: {len(missing_basic_errors)}, 有估值无K线: {len(missing_kline_errors)}")
                
                total_errors = total_kline_errors + total_basic_errors
                if total_errors > 0:
                    # 将异常写入任务队列进行重采修复
                    sql_task = """
                    INSERT IGNORE INTO meta_task_queue (task_type, ts_code, trade_date, error_type, status)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    tasks = []
                    # K线异常
                    for r in order_errors:
                        tasks.append(('kline_audit_repair', r[0], r[1], 'PHYSICAL_ERROR', 'PENDING'))
                    for r in zero_errors:
                        tasks.append(('kline_audit_repair', r[0], r[1], 'PHYSICAL_ERROR', 'PENDING'))
                    # 估值/关系对账异常
                    for r in price_diff_errors:
                        tasks.append(('valuation_audit_repair', r[0], r[1], 'PRICE_MISMATCH', 'PENDING'))
                    for r in basic_anomaly_errors:
                        tasks.append(('valuation_audit_repair', r[0], r[1], 'VALUATION_ANOMALY', 'PENDING'))
                    for r in missing_basic_errors:
                        tasks.append(('valuation_audit_repair', r[0], r[1], 'MISSING_VALUATION', 'PENDING'))
                    for r in missing_kline_errors:
                        tasks.append(('kline_audit_repair', r[0], r[1], 'MISSING_KLINE', 'PENDING'))
                    
                    await cur.executemany(sql_task, tasks)
                    logger.warning(f"已将 {len(tasks)} 条物理与关系异常记录注入修复队列")
                else:
                    logger.info("✅ 未发现任何物理红线或外键一致性异常")

if __name__ == "__main__":
    checker = InternalConsistencyChecker()
    asyncio.run(checker.run_audit(limit_days=365)) # 扩大扫描范围至 1 年
