import os
import sys
import asyncio
import logging
import json
from datetime import datetime, date
from dotenv import load_dotenv

# Add parent directories to sys.path for shared module imports
current_dir = os.path.dirname(os.path.abspath(__file__))
scf_collector_dir = os.path.dirname(os.path.dirname(current_dir))
if scf_collector_dir not in sys.path:
    sys.path.append(scf_collector_dir)

# Load env before other imports
load_dotenv(os.path.join(scf_collector_dir, '.env'))

from shared.db.connection import execute_query
from shared.db.dao import StockDAO

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RepairExecutor")

class KlineRepairExecutor:
    """
    数据修复执行器: 从 meta_task_queue 读取任务并执行物理回填
    """
    def __init__(self):
        self.dao = StockDAO()

    async def fetch_pending_tasks(self, limit=100):
        sql = "SELECT * FROM meta_task_queue WHERE status = 'PENDING' LIMIT %s"
        return await execute_query(sql, (limit,), is_select=True)

    async def update_task_status(self, task_id, status, error_msg=None):
        sql = "UPDATE meta_task_queue SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        await execute_query(sql, (status, task_id), is_select=False)

    async def repair_kline(self, task):
        """ 执行 K 线物理修复 (不复权口径) 并记录历史 """
        context = json.loads(task['context'])
        target_rec = context.get('record')
        local_rec = context.get('record_local') # 假设我们在 audit 时存了 local 记录，如果没有，我们需要查一下
        if not target_rec:
            logger.error(f"No target record found in task {task['id']}")
            return False

        # 单位转换: Tushare 原始数据是 '手', stock_kline_daily 存的是 '股'
        vol_shares = float(target_rec['volume']) * 100.0
        
        # 交易日期格式对齐
        raw_date = target_rec['trade_date']
        db_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if '-' not in raw_date else raw_date

        try:
            # 1. 记录修复前的旧值 (如果 context 没存，则实时查一次)
            if not local_rec:
                sql_old = "SELECT * FROM stock_kline_daily WHERE ts_code = %s AND trade_date = %s"
                old_rows = await execute_query(sql_old, (task['ts_code'], db_date), is_select=True)
                local_rec = old_rows[0] if old_rows else {}

            # 2. 执行修复
            sql = """
            INSERT INTO stock_kline_daily (
                ts_code, trade_date, open, high, low, close, pre_close, 
                pct_chg, volume, amount
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE 
                open = VALUES(open), high = VALUES(high), low = VALUES(low), 
                close = VALUES(close), pre_close = VALUES(pre_close), 
                pct_chg = VALUES(pct_chg), volume = VALUES(volume), 
                amount = VALUES(amount)
            """
            params = (
                target_rec['ts_code'], db_date, target_rec['open'],
                target_rec['high'], target_rec['low'], target_rec['close'],
                target_rec['pre_close'], target_rec['pct_chg'], vol_shares,
                target_rec['amount']
            )
            await execute_query(sql, params, is_select=False)

            # 3. 记录到 meta_repair_history
            sql_hist = """
            INSERT INTO meta_repair_history (task_id, ts_code, trade_date, repair_type, old_value, new_value)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            new_val_json = json.dumps({"volume_shares": vol_shares, **target_rec})
            await execute_query(sql_hist, (
                task['id'], task['ts_code'], db_date, 'KLINE_DATA_FIX', 
                json.dumps(local_rec, default=str), new_val_json
            ), is_select=False)

            return True
        except Exception as e:
            logger.error(f"Failed to repair task {task['id']} for {task['ts_code']}: {e}")
            return False

    async def repair_kline_batch(self, task):
        """ 执行全量覆盖修复某日数据 """
        trade_date = task['trade_date']
        db_date = trade_date.strftime('%Y-%m-%d') if isinstance(trade_date, (date, datetime)) else str(trade_date)
        logger.info(f"Executing BATCH repair for date: {db_date}")
        
        try:
            # 1. 从 Tushare 获取全量
            from shared.collectors.tushare_cl import TushareCollector
            ts_cl = TushareCollector()
            batch_data = await ts_cl.fetch_batch_daily_kline(db_date)
            
            if not batch_data:
                logger.warning(f"No batch data fetched from Tushare for {db_date}")
                return False

            # 2. 调用 DAO 批量保存 (DAO 内部已有 ON DUPLICATE KEY UPDATE 逻辑)
            # 注意: DAO.save_kline_data 会把 volume 处理为 '股' (如果输入是手，需要处理)
            # 但是 fetch_batch_daily_kline 返回的是 KLineModel 列表，
            # 我需要检查 save_kline_data 是否处理了单位。
            # 查看之前的 DAO 代码，save_kline_data 并没有自动 *100。
            # 所以我们需要在这里手动处理单位，或者修改 DAO。
            
            # 为了安全，我们在这里处理
            for item in batch_data:
                if hasattr(item, 'volume'):
                    item.volume = float(item.volume) * 100.0
                elif isinstance(item, dict):
                    item['volume'] = float(item['volume']) * 100.0

            await self.dao.save_kline_data(batch_data)
            return True
        except Exception as e:
            logger.error(f"Failed to execute batch repair for {db_date}: {e}")
            return False

    async def run(self):
        tasks = await self.fetch_pending_tasks(limit=500)
        if not tasks:
            logger.info("No pending repair tasks found in meta_task_queue.")
            return

        logger.info(f"Starting repair mission for {len(tasks)} tasks...")
        success_count = 0
        for task in tasks:
            success = False
            if task['task_type'] == 'REPAIR_KLINE':
                success = await self.repair_kline(task)
            elif task['task_type'] == 'REPAIR_KLINE_BATCH':
                success = await self.repair_kline_batch(task)
            
            if success:
                await self.update_task_status(task['id'], 'SUCCESS')
                success_count += 1
                if success_count % 50 == 0:
                    logger.info(f"Progress: {success_count}/{len(tasks)} fixed.")
            else:
                await self.update_task_status(task['id'], 'FAILED')

        logger.info(f"Repair mission completed. Success: {success_count}, Total: {len(tasks)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Run in loop mode")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds for loop mode")
    args = parser.parse_args()
    
    executor = KlineRepairExecutor()
    
    async def main():
        if args.loop:
            logger.info(f"Starting RepairExecutor in LOOP mode (interval: {args.interval}s)")
            while True:
                await executor.run()
                await asyncio.sleep(args.interval)
        else:
            await executor.run()
            
    asyncio.run(main())
