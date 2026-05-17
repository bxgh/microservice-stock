import os
import sys
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv
import pandas as pd

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
from shared.collectors.akshare_cl import AkShareCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("ShadowValidator")

class ShadowValidator:
    def __init__(self):
        self.collector = AkShareCollector()
        self.pool = None

    async def get_samples(self, trade_date: str, sample_rate: float = 0.01) -> List[Dict[str, Any]]:
        """从数据库中随机抽取样本"""
        if not self.pool:
            self.pool = await DBManager.get_pool()
            
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 1. 先统计当日总数
                sql_count = "SELECT COUNT(*) FROM stock_kline_daily WHERE trade_date = %s"
                await cur.execute(sql_count, (trade_date,))
                total = (await cur.fetchone())[0]
                
                if total == 0:
                    return []
                
                limit = max(1, int(total * sample_rate))
                logger.info(f"日期 {trade_date} 总行数: {total}, 采样目标: {limit}")
                
                # 2. 随机采样
                sql_sample = """
                SELECT ts_code, open, high, low, close, volume, amount 
                FROM stock_kline_daily 
                WHERE trade_date = %s 
                ORDER BY RAND() 
                LIMIT %s
                """
                await cur.execute(sql_sample, (trade_date, limit))
                columns = ['ts_code', 'open', 'high', 'low', 'close', 'volume', 'amount']
                rows = await cur.fetchall()
                return [dict(zip(columns, r)) for r in rows]

    async def validate_one(self, trade_date: str, local_data: Dict[str, Any]):
        """验证单条记录"""
        ts_code = local_data['ts_code']
        try:
            # 获取影子源数据
            ak_klines = await self.collector.fetch_daily_kline(ts_code, trade_date)
            if not ak_klines:
                logger.warning(f"影子源缺失数据: {ts_code} @ {trade_date}")
                return None

            ak = ak_klines[0]
            
            # 对比逻辑 (容差 0.01)
            discrepancies = []
            for field in ['open', 'high', 'low', 'close']:
                diff = abs(float(local_data[field]) - float(getattr(ak, field)))
                if diff > 0.011: # 允许微小舍入误差
                    discrepancies.append(f"{field}: local={local_data[field]}, shadow={getattr(ak, field)}")
            
            if discrepancies:
                logger.error(f"❌ 发现差异! {ts_code} @ {trade_date}: {'; '.join(discrepancies)}")
                return {
                    'ts_code': ts_code,
                    'trade_date': trade_date,
                    'error_type': 'PRICE_MISMATCH',
                    'context': {'local': local_data, 'shadow': ak.__dict__, 'diff': discrepancies}
                }
            else:
                logger.info(f"✅ 对账成功: {ts_code} @ {trade_date}")
                return "OK"
        except Exception as e:
            logger.error(f"验证过程出错 {ts_code}: {e}")
            return None

    async def run_audit(self, trade_date: str):
        """执行完整对账流程"""
        samples = await self.get_samples(trade_date)
        if not samples:
            logger.info(f"日期 {trade_date} 无数据可对账")
            return

        logger.info(f"开始对账 {len(samples)} 个样本...")
        
        # 并行执行 (控制并发数为 5，防止 AkShare 被封)
        semaphore = asyncio.Semaphore(5)
        
        async def sem_validate(s):
            async with semaphore:
                res = await self.validate_one(trade_date, s)
                await asyncio.sleep(0.5) # 稍微避让
                return res

        results = await asyncio.gather(*[sem_validate(s) for s in samples])
        
        # 统计结果
        mismatches = [r for r in results if isinstance(r, dict)]
        logger.info(f"对账结束. 成功: {results.count('OK')}, 差异: {len(mismatches)}, 失败: {results.count(None)}")
        
        # 写入 meta_task_queue
        if mismatches:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = """
                    INSERT INTO meta_task_queue (task_type, ts_code, trade_date, error_type, context, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    tasks = [
                        ('kline_price_fix', m['ts_code'], m['trade_date'], 'PRICE_MISMATCH', 
                         pd.io.json.dumps(m['context']), 'PENDING') 
                        for m in mismatches
                    ]
                    await cur.executemany(sql, tasks)
                    logger.info(f"已将 {len(tasks)} 条差异记录写入修复队列")

if __name__ == "__main__":
    validator = ShadowValidator()
    # 默认核验最近一个交易日 (2026-05-15)
    asyncio.run(validator.run_audit("2026-05-15"))
