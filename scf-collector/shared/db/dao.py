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

    @staticmethod
    def _format_tushare_date(date_str: str) -> str:
        """将 '20260508' 转换为 '2026-05-08'"""
        if not date_str or not isinstance(date_str, str) or len(date_str) != 8:
            return None
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    @classmethod
    async def save_trading_calendar(cls, data: List[Dict[str, Any]]) -> int:
        """保存交易日历"""
        if not data:
            return 0
        
        sql = """
        INSERT INTO trade_cal (cal_date, exchange, is_open, pretrade_date)
        VALUES (%(cal_date)s, %(exchange)s, %(is_open)s, %(pretrade_date)s)
        ON DUPLICATE KEY UPDATE 
            is_open = VALUES(is_open),
            pretrade_date = VALUES(pretrade_date)
        """
        
        count = 0
        for item in data:
            # 数据转换
            formatted_item = {
                "cal_date": cls._format_tushare_date(item.get('cal_date')),
                "exchange": item.get('exchange'),
                "is_open": int(item.get('is_open', 0)),
                "pretrade_date": cls._format_tushare_date(item.get('pretrade_date'))
            }
            res = await execute_query(sql, formatted_item, is_select=False)
            count += res
            
        logger.info(f"Saved {len(data)} calendar records to trade_cal.")
        return count

    @classmethod
    async def save_stock_list(cls, data: List[Dict[str, Any]]) -> int:
        """保存股票列表"""
        if not data:
            return 0
            
        sql = """
        INSERT INTO stock_basic_info (
            ts_code, symbol, name, area, industry, fullname, enname, cnspell, 
            market, exchange, curr_type, list_status, list_date, delist_date, 
            is_hs, act_name, act_ent_type
        ) VALUES (
            %(ts_code)s, %(symbol)s, %(name)s, %(area)s, %(industry)s, %(fullname)s, %(enname)s, %(cnspell)s, 
            %(market)s, %(exchange)s, %(curr_type)s, %(list_status)s, %(list_date)s, %(delist_date)s, 
            %(is_hs)s, %(act_name)s, %(act_ent_type)s
        ) ON DUPLICATE KEY UPDATE 
            name = VALUES(name),
            area = VALUES(area),
            industry = VALUES(industry),
            list_status = VALUES(list_status),
            delist_date = VALUES(delist_date),
            is_hs = VALUES(is_hs)
        """
        
        count = 0
        for item in data:
            # 日期处理
            item['list_date'] = cls._format_tushare_date(item.get('list_date'))
            item['delist_date'] = cls._format_tushare_date(item.get('delist_date'))
            
            res = await execute_query(sql, item, is_select=False)
            count += res
            
        logger.info(f"Saved {len(data)} stock list records to stock_basic_info.")
        return count
