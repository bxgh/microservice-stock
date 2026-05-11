import logging
from typing import List, Dict, Any
from .connection import execute_query

logger = logging.getLogger(__name__)

class StockDAO:
    """
    数据访问对象 - 处理股票采集相关数据库操作
    """

    @staticmethod
    async def save_kline_data(data: List[Dict[str, Any]]) -> int:
        """
        批量保存 K 线数据 (幂等插入)
        """
        if not data:
            return 0

        # 构建批量插入 SQL
        # 使用 ON DUPLICATE KEY UPDATE 确保幂等性
        sql = """
        INSERT INTO stock_kline_daily (
            ts_code, trade_date, open, high, low, close, 
            pre_close, pct_chg, volume, amount
        ) VALUES (
            %(ts_code)s, %(trade_date)s, %(open)s, %(high)s, %(low)s, %(close)s, 
            %(pre_close)s, %(pct_chg)s, %(volume)s, %(amount)s
        ) ON DUPLICATE KEY UPDATE 
            open = VALUES(open), 
            high = VALUES(high), 
            low = VALUES(low), 
            close = VALUES(close), 
            pre_close = VALUES(pre_close), 
            pct_chg = VALUES(pct_chg), 
            volume = VALUES(volume), 
            amount = VALUES(amount)
        """
        
        # 注意：aiomysql 的 executemany 在某些版本下对 Dict 格式支持有差异
        # 建议手动循环或使用适配格式
        count = 0
        for item in data:
            # 确保日期格式符合 MySQL 要求
            res = await execute_query(sql, item, is_select=False)
            count += res
        
        logger.info(f"Successfully saved {len(data)} records to stock_kline_daily (affected: {count}).")
        return count

    @staticmethod
    async def log_pipeline_run(pipeline_id: str, status: str, error_message: str = None, run_id: str = None, biz_date: str = None) -> int:
        """
        记录任务流水审计 (使用 meta_pipeline_run)
        """
        sql = """
        INSERT INTO meta_pipeline_run (
            run_id, pipeline_id, biz_date, status, error_message, started_at, finished_at
        ) VALUES (
            %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        ) ON DUPLICATE KEY UPDATE 
            status = VALUES(status), 
            error_message = VALUES(error_message), 
            finished_at = CURRENT_TIMESTAMP
        """
        params = (run_id, pipeline_id, biz_date, status, error_message)
        return await execute_query(sql, params, is_select=False)

    @staticmethod
    async def update_data_readiness(biz_date: str, table_name: str, row_count: int) -> int:
        """
        更新数据就绪状态探测表 (绝对对齐 meta_data_readiness)
        """
        sql = """
        INSERT INTO meta_data_readiness (
            table_name, biz_date, storage, record_count, ready_at, status
        ) VALUES (
            %s, %s, 'MYSQL', %s, CURRENT_TIMESTAMP, 'READY'
        ) ON DUPLICATE KEY UPDATE 
            record_count = VALUES(record_count),
            ready_at = CURRENT_TIMESTAMP, 
            status = 'READY'
        """
        params = (table_name, biz_date, row_count)
        return await execute_query(sql, params, is_select=False)
