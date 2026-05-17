import os
import sys
import asyncio
import logging
from datetime import datetime
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
from shared.collectors.tushare_cl import TushareCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("AutoRepairWorker")

class AutoRepairWorker:
    def __init__(self):
        self.collector = TushareCollector()
        self.pool = None

    async def get_pending_tasks(self, limit: int = 1000) -> Dict[str, List[str]]:
        """从队列中获取待处理任务，按日期分组"""
        if not self.pool:
            self.pool = await DBManager.get_pool()
            
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = """
                SELECT ts_code, trade_date 
                FROM meta_task_queue 
                WHERE task_type = 'kline_audit_repair' 
                  AND status = 'PENDING' 
                  AND error_type = 'HOLE'
                LIMIT %s
                """
                await cur.execute(sql, (limit,))
                rows = await cur.fetchall()
                
                tasks_by_day = {}
                for ts_code, trade_date in rows:
                    date_str = trade_date.strftime('%Y-%m-%d') if isinstance(trade_date, datetime) or hasattr(trade_date, 'strftime') else str(trade_date)
                    if date_str not in tasks_by_day:
                        tasks_by_day[date_str] = []
                    tasks_by_day[date_str].append(ts_code)
                return tasks_by_day

    async def repair_day(self, trade_date: str, target_codes: List[str]):
        """修复特定日期的空洞"""
        logger.info(f"正在修复日期: {trade_date} | 目标缺口数: {len(target_codes)}")
        
        try:
            # 1. 批量获取该日行情
            klines = await self.collector.fetch_batch_daily_kline(trade_date)
            fetched_codes = set([k.ts_code for k in klines]) if klines else set()

            # 2. 获取当日停牌列表，用于排除假空洞
            suspensions = await self.collector.fetch_suspensions(trade_date)
            suspended_codes = set([s['ts_code'] for s in suspensions]) if suspensions else set()

            # 3. 批量入库 (UPSERT)
            if klines:
                records = []
                for k in klines:
                    records.append((
                        k.ts_code, k.trade_date, k.open, k.high, k.low, k.close,
                        k.pre_close, k.pct_chg, k.volume, k.amount
                    ))
                
                sql_upsert = """
                INSERT INTO stock_kline_daily (
                    ts_code, trade_date, open, high, low, close, pre_close, pct_chg, volume, amount
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    open=VALUES(open), high=VALUES(high), low=VALUES(low), close=VALUES(close),
                    pre_close=VALUES(pre_close), pct_chg=VALUES(pct_chg), volume=VALUES(volume), amount=VALUES(amount)
                """
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.executemany(sql_upsert, records)

            # 4. 判定任务状态
            # 成功条件：要么补全了数据，要么该股当天确实停牌了
            resolved_codes = fetched_codes.union(suspended_codes)
            remaining_holes = set(target_codes) - resolved_codes
            
            # 5. [新增] AkShare 强力补偿逻辑
            if remaining_holes:
                logger.info(f"日期 {trade_date} 启动 AkShare 补偿，目标: {len(remaining_holes)} 只")
                from shared.collectors.akshare_cl import AkShareCollector
                ak_collector = AkShareCollector()
                
                ak_records = []
                for code in remaining_holes:
                    try:
                        # AkShare 通常需要单点抓取历史
                        ak_klines = await ak_collector.fetch_daily_kline(code, trade_date)
                        if ak_klines:
                            k = ak_klines[0] # 取当日
                            ak_records.append((
                                k.ts_code, k.trade_date, k.open, k.high, k.low, k.close,
                                k.pre_close, k.pct_chg, k.volume, k.amount
                            ))
                            resolved_codes.add(code)
                            logger.info(f"AkShare 补偿成功: {code} @ {trade_date}")
                    except Exception as ak_e:
                        logger.error(f"AkShare 补偿失败 {code}: {ak_e}")
                
                if ak_records:
                    async with self.pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await cur.executemany(sql_upsert, ak_records)

            # 6. 更新任务状态
            success_codes = [c for c in target_codes if c in resolved_codes]
            if success_codes:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        sql_update = """
                        UPDATE meta_task_queue 
                        SET status = 'SUCCESS', updated_at = CURRENT_TIMESTAMP 
                        WHERE task_type = 'kline_audit_repair' 
                          AND trade_date = %s 
                          AND ts_code IN %s
                        """
                        await cur.execute(sql_update, (trade_date, success_codes))
                        logger.info(f"日期 {trade_date} 修复完成: {len(success_codes)}/{len(target_codes)}")

            # 7. [新增] 标记无法解决的硬骨头，防止死循环
            failed_codes = list(set(target_codes) - resolved_codes)
            if failed_codes:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        sql_fail = """
                        UPDATE meta_task_queue 
                        SET status = 'FAILED', updated_at = CURRENT_TIMESTAMP 
                        WHERE task_type = 'kline_audit_repair' 
                          AND trade_date = %s 
                          AND ts_code IN %s
                        """
                        await cur.execute(sql_fail, (trade_date, failed_codes))
                        logger.warning(f"日期 {trade_date} 有 {len(failed_codes)} 只股票无法修复，已标记为 FAILED")

            return True
        except Exception as e:
            logger.error(f"修复日期 {trade_date} 发生异常: {e}")
            return False

    async def run(self):
        logger.info("启动自动修复引擎 v1.0...")
        while True:
            tasks_by_day = await self.get_pending_tasks(limit=2000)
            if not tasks_by_day:
                logger.info("任务队列已空，休眠 60 秒...")
                await asyncio.sleep(60)
                continue

            for day, codes in tasks_by_day.items():
                await self.repair_day(day, codes)
                # Tushare 每分钟限制 200 次，我们在这里稍微稳一点
                await asyncio.sleep(1.2)

if __name__ == "__main__":
    worker = AutoRepairWorker()
    asyncio.run(worker.run())
