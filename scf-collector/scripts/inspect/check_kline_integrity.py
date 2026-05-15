import asyncio
import logging
import argparse
import json
import os
from datetime import datetime, date
from typing import List, Dict, Any

# 导入共享 DAO
from shared.db.dao import StockDAO
from shared.db.connection import execute_query, DBManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class KlineIntegrityChecker:
    """
    日线数据完整性巡检工具
    """
    def __init__(self, mode: str = 'delta'):
        self.mode = mode
        self.today = date.today().strftime('%Y-%m-%d')
        self.batch_size = 50  # 每批处理的股票数

    async def get_expected_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """获取指定范围内的所有交易日"""
        sql = """
        SELECT cal_date FROM trade_cal 
        WHERE cal_date BETWEEN %s AND %s 
          AND is_open = 1 
          AND exchange IN ('SSE', 'SH')
        ORDER BY cal_date ASC
        """
        rows = await execute_query(sql, (start_date, end_date), is_select=True)
        return [str(row['cal_date']) for row in rows] if rows else []

    async def get_check_range(self) -> (str, str):
        """确定校验日期范围"""
        if self.mode == 'full':
            # 基准模式：从最早的上市日期开始（暂定 1990-12-19 A股开市）
            return "1990-12-19", self.today
        else:
            # 增量模式：从上次校验成功日期开始
            sql = "SELECT config_value FROM meta_config WHERE config_key = 'last_kline_check_date'"
            rows = await execute_query(sql, is_select=True)
            start_date = rows[0]['config_value'] if rows else "2026-01-01"
            return start_date, self.today

    async def run(self):
        start_date, end_date = await self.get_check_range()
        logger.info(f"Starting Kline Integrity Check | Mode: {self.mode} | Range: {start_date} to {end_date}")

        # 1. 获取所有待检查股票
        sql_stocks = "SELECT ts_code, list_date FROM stock_basic_info WHERE list_status = 'L'"
        stocks = await execute_query(sql_stocks, is_select=True)
        if not stocks:
            logger.error("No active stocks found in stock_basic_info.")
            return

        # 2. 获取基准交易日历 (全局范围)
        all_cal_days = await self.get_expected_trading_days(start_date, end_date)
        if not all_cal_days:
            logger.warning(f"No trading days found between {start_date} and {end_date}")
            return

        total_stocks = len(stocks)
        missing_count = 0

        # 3. 分批处理股票
        for i in range(0, total_stocks, self.batch_size):
            batch = stocks[i:i + self.batch_size]
            batch_codes = [s['ts_code'] for s in batch]
            
            logger.info(f"Checking batch {i//self.batch_size + 1}/{(total_stocks-1)//self.batch_size + 1} ({len(batch_codes)} stocks)...")
            
            # 针对当前批次，查询实际存在的日期
            # 使用 LEFT JOIN 查找缺失值可能由于数据量过大导致索引失效，此处采用 Python 集合比对
            # 为了性能，单次查询该批次股票在指定范围内的所有记录
            sql_exists = """
            SELECT ts_code, trade_date 
            FROM stock_kline_daily 
            WHERE ts_code IN ({}) AND trade_date BETWEEN %s AND %s
            """.format(','.join(['%s'] * len(batch_codes)))
            
            exists_rows = await execute_query(sql_exists, (*batch_codes, start_date, end_date), is_select=True)
            
            # 组织为映射表: ts_code -> set(trade_dates)
            exists_map = {code: set() for code in batch_codes}
            for row in exists_rows:
                exists_map[row['ts_code']].add(str(row['trade_date']))

            # 4. 比对空洞
            for stock in batch:
                code = stock['ts_code']
                list_date = str(stock['list_date'])
                
                # 该股票应有的交易日：从 max(start_date, list_date) 开始
                effective_start = max(start_date, list_date)
                expected_days = [d for d in all_cal_days if d >= effective_start]
                
                actual_days = exists_map.get(code, set())
                gaps = [d for d in expected_days if d not in actual_days]
                
                if gaps:
                    missing_count += len(gaps)
                    logger.warning(f"Found {len(gaps)} gaps for {code}")
                    await self.submit_repair_tasks(code, gaps)

        # 5. 更新校验锚点 (仅在增量模式或全量执行成功后)
        if self.mode == 'delta' or (self.mode == 'full' and missing_count == 0):
             sql_update_anchor = """
             INSERT INTO meta_config (config_key, config_value, description)
             VALUES ('last_kline_check_date', %s, 'Last successful kline integrity check date')
             ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)
             """
             await execute_query(sql_update_anchor, (end_date,), is_select=False)

        logger.info(f"Integrity Check Finished. Total gaps found: {missing_count}")
        await DBManager.close_pool()

    async def submit_repair_tasks(self, ts_code: str, gaps: List[str]):
        """将缺失日期提交至任务队列"""
        # 任务去重或合并处理 (此处简便起见，每日期一条任务)
        sql = """
        INSERT IGNORE INTO meta_task_queue (task_type, priority, params, status)
        VALUES ('kline_refetch', 5, %s, 'pending')
        """
        for g_date in gaps:
            params = json.dumps({"ts_code": ts_code, "trade_date": g_date.replace('-', '')})
            await execute_query(sql, (params,), is_select=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kline Integrity Checker")
    parser.add_argument("--mode", choices=["full", "delta"], default="delta", help="Check mode: full or delta")
    args = parser.parse_args()

    # 确保环境变量存在 (本地测试建议使用 .env)
    asyncio.run(KlineIntegrityChecker(mode=args.mode).run())
