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
            pre_close, `change`, pct_chg, vol, amount
        ) VALUES (
            %(ts_code)s, %(trade_date)s, %(open)s, %(high)s, %(low)s, %(close)s, 
            %(pre_close)s, %(change)s, %(pct_chg)s, %(vol)s, %(amount)s
        ) ON DUPLICATE KEY UPDATE 
            open = VALUES(open), 
            high = VALUES(high), 
            low = VALUES(low), 
            close = VALUES(close), 
            pre_close = VALUES(pre_close), 
            `change` = VALUES(`change`), 
            pct_chg = VALUES(pct_chg), 
            vol = VALUES(vol), 
            amount = VALUES(amount),
            updated_at = CURRENT_TIMESTAMP
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
    async def log_pipeline_run(pipeline_name: str, status: str, error_msg: str = None, run_id: str = None) -> int:
        """
        记录任务流水审计
        """
        sql = """
        INSERT INTO pipeline_run (
            run_id, pipeline_name, status, error_msg, start_at, end_at
        ) VALUES (
            %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        ) ON DUPLICATE KEY UPDATE 
            status = VALUES(status), 
            error_msg = VALUES(error_msg), 
            end_at = CURRENT_TIMESTAMP
        """
        params = (run_id, pipeline_name, status, error_msg)
        return await execute_query(sql, params, is_select=False)

    @staticmethod
    async def update_data_readiness(trade_date: str, source: str, row_count: int) -> int:
        """
        更新数据就绪状态探测表
        """
        sql = """
        INSERT INTO data_readiness (
            data_source, trade_date, ready_at, status, row_count
        ) VALUES (
            %s, %s, CURRENT_TIMESTAMP, 'ready', %s
        ) ON DUPLICATE KEY UPDATE 
            ready_at = CURRENT_TIMESTAMP, 
            status = 'ready', 
            row_count = VALUES(row_count)
        """
        params = (source, trade_date, row_count)
        return await execute_query(sql, params, is_select=False)
