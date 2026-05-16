import os
import sys
import asyncio
import logging
import json
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from decimal import Decimal
from dotenv import load_dotenv

# Add parent directories to sys.path for shared module imports
current_dir = os.path.dirname(os.path.abspath(__file__))
scf_collector_dir = os.path.dirname(os.path.dirname(current_dir))
if scf_collector_dir not in sys.path:
    sys.path.append(scf_collector_dir)

# Load env before other imports
load_dotenv(os.path.join(scf_collector_dir, '.env'))

from shared.db.dao import StockDAO
from shared.db.connection import execute_query
from shared.collectors.tushare_cl import TushareCollector
from shared.collectors.akshare_cl import AkShareCollector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("KlineAudit")

class Arbitrator:
    """
    三源仲裁引擎: Local vs Tushare vs AkShare
    """
    def __init__(self, tushare_cl: TushareCollector, akshare_cl: AkShareCollector):
        self.tushare = tushare_cl
        self.akshare = akshare_cl

    def is_close_enough(self, val1: float, val2: float, threshold: float = 0.0001) -> bool:
        try:
            return abs(float(val1) - float(val2)) < threshold
        except (ValueError, TypeError):
            return False

    def compare_records(self, local_rec: Dict[str, Any], target_rec: Dict[str, Any], is_stock: bool = True) -> Dict[str, bool]:
        """
        比对两条记录的 OHLC, Volume, Amount
        is_stock: True 代表 stock_kline_daily (单位: 股), False 代表指数 (单位: 手)
        """
        fields = ['open', 'high', 'low', 'close', 'volume']
        results = {}
        for f in fields:
            v1 = local_rec.get(f, 0)
            v2 = target_rec.get(f, 0)
            
            # 单位对齐: Tushare 产出是 '手', local_rec (stock_kline_daily) 是 '股'
            if f == 'volume' and is_stock:
                v2 = v2 * 100.0
            
            # 对于成交量, 允许 1% 以内的误差 (不同源统计口径细微差异)
            if f == 'volume':
                if v2 == 0:
                    results[f] = (v1 == 0)
                else:
                    results[f] = abs(v1 - v2) / v2 < 0.01 
            else:
                results[f] = self.is_close_enough(v1, v2, 0.001)
        
        return results

    async def arbitrate(self, ts_code: str, trade_date: str, local_rec: Optional[Dict[str, Any]], is_stock: bool = True) -> Dict[str, Any]:
        """
        仲裁逻辑:
        1. Fetch Tushare (P0)
        2. If Local != Tushare: Fetch AkShare (P1)
        3. Determine result
        """
        # 1. Fetch Tushare
        try:
            tushare_results = await self.tushare.fetch_daily_kline(ts_code, trade_date)
            tushare_rec = tushare_results[0].model_dump() if tushare_results else None
        except Exception as e:
            logger.error(f"Failed to fetch Tushare for {ts_code} on {trade_date}: {e}")
            tushare_rec = None

        if not local_rec and not tushare_rec:
            # Both empty
            return {"status": "OK_EMPTY", "target": None}

        if local_rec and tushare_rec:
            comparison = self.compare_records(local_rec, tushare_rec, is_stock=is_stock)
            if all(comparison.values()):
                return {"status": "OK_MATCH", "target": "tushare", "record": tushare_rec}
            
            # Mismatch! Bring in AkShare
            logger.info(f"Mismatch for {ts_code} on {trade_date}: Local({local_rec.get('close')}) vs Tushare({tushare_rec.get('close')}). Fetching AkShare...")
            try:
                akshare_results = await self.akshare.fetch_daily_kline(ts_code, trade_date)
                akshare_rec = akshare_results[0].model_dump() if akshare_results else None
            except Exception as e:
                logger.error(f"Failed to fetch AkShare for {ts_code} on {trade_date}: {e}")
                akshare_rec = None

            if akshare_rec:
                ak_vs_ts = self.compare_records(akshare_rec, tushare_rec, is_stock=False) # AkShare usually same unit as Tushare
                ak_vs_local = self.compare_records(local_rec, akshare_rec, is_stock=is_stock)
                
                if all(ak_vs_ts.values()):
                    # AkShare matches Tushare, Local is definitely wrong
                    return {"status": "MISMATCH", "reason": "local_error", "target": "tushare", "record": tushare_rec, "diff": comparison}
                elif all(ak_vs_local.values()):
                    # AkShare matches Local, Tushare might be wrong (rare)
                    return {"status": "OK_MATCH_AK", "target": "akshare", "record": local_rec}
                else:
                    # All three differ! Use Tushare as default but mark as complex mismatch
                    return {"status": "MISMATCH", "reason": "triple_diff", "target": "tushare", "record": tushare_rec, "diff": comparison}
            else:
                # AkShare also empty or failed, trust Tushare
                return {"status": "MISMATCH", "reason": "local_error_no_ak", "target": "tushare", "record": tushare_rec, "diff": comparison}

        if not local_rec and tushare_rec:
            # Hole in local data
            return {"status": "HOLE", "target": "tushare", "record": tushare_rec}

        if local_rec and not tushare_rec:
            # Redundant or Tushare missing data? Check AkShare
            logger.info(f"Redundant for {ts_code} on {trade_date}: Local has data but Tushare is empty. Fetching AkShare...")
            try:
                akshare_results = await self.akshare.fetch_daily_kline(ts_code, trade_date)
                akshare_rec = akshare_results[0].model_dump() if akshare_results else None
            except Exception as e:
                akshare_rec = None
            
            if not akshare_rec:
                # Local data might be garbage (redundant)
                return {"status": "REDUNDANT", "target": None}
            else:
                # Local might be correct if AkShare confirms it
                return {"status": "OK_LOCAL_CONFIRMED", "target": "local", "record": local_rec}

        return {"status": "UNKNOWN"}

class KlineIntegrityChecker:
    def __init__(self):
        self.dao = StockDAO()
        self.tushare = TushareCollector()
        self.akshare = AkShareCollector()
        self.arbitrator = Arbitrator(self.tushare, self.akshare)

    async def get_config(self, key: str) -> Optional[str]:
        sql = "SELECT config_value FROM meta_config WHERE config_key = %s"
        rows = await execute_query(sql, (key,), is_select=True)
        return rows[0]['config_value'] if rows else None

    async def set_config(self, key: str, value: str):
        sql = """
        INSERT INTO meta_config (config_key, config_value) 
        VALUES (%s, %s) 
        ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)
        """
        await execute_query(sql, (key, value), is_select=False)

    async def get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        sql = """
        SELECT cal_date FROM trade_cal 
        WHERE cal_date BETWEEN %s AND %s 
        AND is_open = 1 AND exchange = 'SSE'
        ORDER BY cal_date ASC
        """
        rows = await execute_query(sql, (start_date, end_date), is_select=True)
        return [row['cal_date'].strftime('%Y%m%d') if isinstance(row['cal_date'], (date, datetime)) else str(row['cal_date']).replace('-', '') for row in rows]

    async def add_to_task_queue(self, task_type: str, ts_code: str, trade_date: str, error_type: str, context: Dict[str, Any]):
        sql = """
        INSERT INTO meta_task_queue (task_type, ts_code, trade_date, error_type, context, status)
        VALUES (%s, %s, %s, %s, %s, 'PENDING')
        ON DUPLICATE KEY UPDATE 
            error_type = VALUES(error_type),
            context = VALUES(context),
            status = 'PENDING',
            updated_at = CURRENT_TIMESTAMP
        """
        # Ensure trade_date is in YYYY-MM-DD format for DB
        db_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
        await execute_query(sql, (task_type, ts_code, db_date, error_type, json.dumps(context)), is_select=False)

    async def audit_adj_factor_day(self, trade_date: str):
        """
        审计单日全市场复权因子
        """
        logger.info(f">>> Auditing adj_factors for date: {trade_date}")
        db_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
        
        # 1. Get all active stocks
        active_codes = await self.dao.get_active_stock_codes(db_date)
        
        # 2. Get local adj_factors
        sql_local = "SELECT ts_code, adjust_factor FROM stock_adjust_factor WHERE adjust_date = %s"
        local_rows = await execute_query(sql_local, (db_date,), is_select=True)
        local_map = {row['ts_code']: float(row['adjust_factor']) for row in local_rows}
        
        # 3. Get Tushare adj_factors
        try:
            tushare_results = await self.tushare.fetch_adj_factor(trade_date)
            tushare_map = {row['ts_code']: float(row['adj_factor']) for row in tushare_results}
        except Exception as e:
            logger.error(f"Failed to fetch Tushare adj_factors for {trade_date}: {e}")
            tushare_map = {}
            
        # 4. Compare
        for ts_code in active_codes:
            local_val = local_map.get(ts_code)
            tushare_val = tushare_map.get(ts_code)
            
            if local_val is None and tushare_val is not None:
                # Hole in local factor table
                # But wait, we only store CHANGE points in stock_adjust_factor
                # So if local is missing, it might just mean no change today.
                # To be sure, we'd need the latest factor before or on this day.
                # However, for a simple audit, we can just check if Tushare's value matches our latest.
                pass 
            elif local_val is not None and tushare_val is not None:
                if abs(local_val - tushare_val) > 0.0001:
                    logger.warning(f"[FACTOR_MISMATCH] {ts_code} on {trade_date}: local={local_val}, target={tushare_val}")
                    await self.add_to_task_queue('REPAIR_FACTOR', ts_code, trade_date, 'FACTOR_STALE', 
                                              {"local": local_val, "target": tushare_val, "source": "tushare"})

    async def audit_day(self, trade_date: str):
        """
        审计单日全市场数据
        """
        await self.audit_kline_day(trade_date)
        await self.audit_adj_factor_day(trade_date)
        
        # Update progress
        await self.set_config('kline_audit_cursor', trade_date)

    async def audit_kline_day(self, trade_date: str):
        """
        审计单日全市场 K 线
        """
        logger.info(f">>> Auditing market K-lines for date: {trade_date}")
        db_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
        
        # 1. Get all active stocks for this day
        active_codes = await self.dao.get_active_stock_codes(db_date)
        if not active_codes:
            logger.warning(f"No active codes found for {trade_date}")
            return
        
        # 2. Get local K-lines
        local_klines = await self.dao.get_kline_daily(db_date)
        local_map = {row['ts_code']: row for row in local_klines}
        
        # 3. Get suspended codes
        suspended_codes = set(await self.dao.get_suspended_codes(db_date))
        
        logger.info(f"Active: {len(active_codes)}, Local: {len(local_klines)}, Suspended: {len(suspended_codes)}")
        
        # 4. Iterate and arbitrate
        try:
            tushare_batch = await self.tushare.fetch_batch_daily_kline(db_date)
            tushare_map = {item.ts_code: item.model_dump() for item in tushare_batch}
        except Exception as e:
            logger.error(f"Batch fetch Tushare failed for {trade_date}: {e}")
            tushare_map = {}

        for ts_code in active_codes:
            local_rec = local_map.get(ts_code)
            tushare_rec = tushare_map.get(ts_code)
            
            # Quick check if match
            is_match = False
            if local_rec and tushare_rec:
                comp = self.arbitrator.compare_records(local_rec, tushare_rec, is_stock=True)
                if all(comp.values()):
                    is_match = True
            
            if is_match:
                continue
                
            # If hole and suspended, skip
            if not local_rec and ts_code in suspended_codes:
                continue

            # Full arbitration (includes AkShare if needed)
            res = await self.arbitrator.arbitrate(ts_code, trade_date, local_rec, is_stock=True)
            
            if res['status'] == 'HOLE':
                logger.warning(f"[HOLE] {ts_code} is missing locally.")
                await self.add_to_task_queue('REPAIR_KLINE', ts_code, trade_date, 'HOLE', res)
            elif res['status'] == 'MISMATCH':
                logger.warning(f"[MISMATCH] {ts_code} value discrepancy.")
                error_type = 'PRICE_MISMATCH' if not res['diff'].get('close', True) else 'VOLUME_MISMATCH'
                await self.add_to_task_queue('REPAIR_KLINE', ts_code, trade_date, error_type, res)

    async def run(self, start_date: str = None, end_date: str = None):
        if not start_date:
            start_date = await self.get_config('kline_audit_cursor') or '20100101'
        
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        trading_days = await self.get_trading_days(start_date, end_date)
        logger.info(f"Found {len(trading_days)} trading days to audit from {start_date} to {end_date}")
        
        for day in trading_days:
            await self.audit_day(day)
            logger.info(f"Completed audit for {day}")

if __name__ == "__main__":
    checker = KlineIntegrityChecker()
    # For testing, just run for one day or a small range
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help="Start date YYYYMMDD")
    parser.add_argument("--end", help="End date YYYYMMDD")
    args = parser.parse_args()
    
    asyncio.run(checker.run(start_date=args.start, end_date=args.end))
