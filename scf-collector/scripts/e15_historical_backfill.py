import sys
import os
import asyncio
import logging
import datetime
import uuid

# 1. 强力路径解析，确保能加载 shared 模块
current_dir = os.path.dirname(os.path.abspath(__file__)) # scf-collector/scripts
project_root = os.path.dirname(current_dir) # scf-collector
workspace_root = os.path.dirname(project_root) # microservice-stock

sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "functions", "daily_quotes"))
sys.path.insert(0, os.path.join(project_root, "shared"))

# 加载 scf-collector 的 .env 文件 (包含数据库 MYSQL_* 及 TUSHARE_TOKEN 变量)
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'), override=True)

# 设置基本的控制台日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("historical_backfill")

# 引入自定义模块
from shared.collectors.tushare_cl import TushareCollector
from shared.collectors.akshare_cl import AkShareCollector
from shared.db.dao import StockDAO
from shared.db.connection import DBManager

async def get_trading_days() -> list:
    """获取 2015-01-01 至今的所有 A 股交易日"""
    sql = """
    SELECT cal_date FROM trade_cal 
    WHERE cal_date >= '2015-01-01' AND cal_date <= '2026-05-19' 
    AND is_open = 1 AND exchange IN ('SSE', 'SH') 
    ORDER BY cal_date
    """
    rows = await DBManager.get_pool()
    # Execute query directly
    from shared.db.connection import execute_query
    res = await execute_query(sql, is_select=True)
    days = []
    for r in res:
        d = r['cal_date']
        if isinstance(d, datetime.date):
            days.append(d.strftime('%Y-%m-%d'))
        else:
            days.append(str(d))
    return days

async def audit_coverage(trading_days: list) -> dict:
    """物理对账审计，得出每个表在 2026 交易日中缺失的具体日期列表"""
    from shared.db.connection import execute_query
    
    tables = {
        "stock_suspensions": "trade_date",
        "ods_event_limit_pool": "trade_date",
        "ods_margin_total": "trade_date",
        "ods_margin_detail": "trade_date",
        "ods_market_breadth_daily": "trade_date"
    }
    
    missing_dict = {}
    
    for table, date_col in tables.items():
        try:
            sql = f"SELECT DISTINCT {date_col} FROM {table} WHERE {date_col} >= '2015-01-01' AND {date_col} <= '2026-05-19'"
            res = await execute_query(sql, is_select=True)
            dates_in_db = set()
            for r in res:
                d = r[date_col]
                if isinstance(d, datetime.date):
                    dates_in_db.add(d.strftime('%Y-%m-%d'))
                else:
                    dates_in_db.add(str(d))
            
            missing_days = [d for d in trading_days if d not in dates_in_db]
            missing_dict[table] = missing_days
            logger.info(f"Table: {table:25} | Covered: {len(dates_in_db):3}/{len(trading_days):3} | Missing: {len(missing_days):3} days")
        except Exception as e:
            logger.error(f"Error auditing table {table}: {e}")
            missing_dict[table] = list(trading_days)
            
    return missing_dict

async def main():
    logger.info("Initializing historical backfill process...")
    
    # 1. 实例化采集器
    try:
        collector_ts = TushareCollector()
        collector_ak = AkShareCollector()
    except Exception as e:
        logger.error(f"Failed to initialize collectors: {e}")
        return
        
    # 2. 获取交易日历
    trading_days = await get_trading_days()
    logger.info(f"Total A-share trading days from 2015: {len(trading_days)}")
    if not trading_days:
        logger.error("No trading calendar data found. Make sure trade_cal has 2015 dates.")
        return
        
    # 3. 对账审计
    missing_dict = await audit_coverage(trading_days)
    
    # 统计总共需要补全的项数
    total_suspensions_missing = len(missing_dict.get("stock_suspensions", []))
    total_limits_missing = len(missing_dict.get("ods_event_limit_pool", []))
    total_margin_total_missing = len(missing_dict.get("ods_margin_total", []))
    total_margin_detail_missing = len(missing_dict.get("ods_margin_detail", []))
    total_breadth_missing = len(missing_dict.get("ods_market_breadth_daily", []))
    
    total_tasks = (total_suspensions_missing + total_limits_missing + 
                   max(total_margin_total_missing, total_margin_detail_missing) + total_breadth_missing)
                   
    if total_tasks == 0:
        logger.info("Excellent! All E15 tables are already 100% complete for history since 2015.")
        return
        
    logger.info(f"Start backfilling... Total dates missing components: "
                f"Suspensions={total_suspensions_missing}, LimitPool={total_limits_missing}, "
                f"MarginTotal={total_margin_total_missing}, MarginDetail={total_margin_detail_missing}, "
                f"Breadth={total_breadth_missing}")
                
    # 4. 按日期逐日补全历史数据
    for idx, trade_date in enumerate(trading_days):
        logger.info(f"\n==================== [{idx+1}/{len(trading_days)}] Date: {trade_date} ====================")
        
        # A. 停复牌补全
        if trade_date in missing_dict.get("stock_suspensions", []):
            logger.info(f"-> Backfilling stock_suspensions for {trade_date}...")
            try:
                suspend_raw = await collector_ts.fetch_suspend_d(trade_date)
                if suspend_raw:
                    cnt = await StockDAO.save_suspend_calendar(suspend_raw)
                    logger.info(f"   Successfully saved {cnt} suspensions.")
                else:
                    logger.info("   No suspensions reported for this date.")
                await asyncio.sleep(1.0) # Flow control
            except Exception as e:
                logger.error(f"   Failed to sync suspensions for {trade_date}: {e}")
                
        # B. 涨跌停池补全
        if trade_date in missing_dict.get("ods_event_limit_pool", []):
            logger.info(f"-> Backfilling ods_event_limit_pool for {trade_date}...")
            try:
                # Tushare 涨停 + 跌停 + 连板
                tushare_raw = await collector_ts.fetch_limit_list(trade_date)
                limit_records = []
                
                for x in tushare_raw:
                    limit_type = x.get('limit_type') or x.get('limit')
                    pool_type = 'zt' if limit_type == 'U' or '涨停' in str(limit_type) else ('dt' if limit_type == 'D' or '跌停' in str(limit_type) else None)
                    if not pool_type:
                        continue
                    
                    record = {
                        'trade_date': trade_date,
                        'ts_code': x.get('ts_code'),
                        'name': x.get('name'),
                        'pool_type': pool_type,
                        'close': x.get('close'),
                        'pct_chg': x.get('pct_chg'),
                        'amount': x.get('amount'),
                        'first_limit_time': x.get('first_time'),
                        'last_limit_time': x.get('last_time'),
                        'board_height': x.get('board_height'),
                        'seal_money': x.get('fd_amount'),
                        'open_times': x.get('open_times'),
                        'data_source': 'tushare'
                    }
                    limit_records.append(record)
                    
                    # 连板
                    bh = x.get('board_height')
                    if pool_type == 'zt' and bh and int(bh) >= 2:
                        lian_record = dict(record)
                        lian_record['pool_type'] = 'lian'
                        limit_records.append(lian_record)
                
                await asyncio.sleep(1.0) # Flow control
                
                # AkShare 炸板池
                try:
                    zb_data = await collector_ak.fetch_limit_pool(trade_date, 'zb')
                    for x in zb_data:
                        record = dict(x)
                        record['trade_date'] = trade_date
                        record['pool_type'] = 'zb'
                        record['data_source'] = 'akshare'
                        limit_records.append(record)
                except Exception as ak_e:
                    logger.warning(f"   Failed to fetch 'zb' pool from AkShare for {trade_date}: {ak_e}")
                
                if limit_records:
                    cnt = await StockDAO.save_limit_pool(limit_records)
                    await StockDAO.update_data_readiness(trade_date, "ods_event_limit_pool", len(limit_records))
                    logger.info(f"   Successfully saved {cnt} records to limit pool.")
                else:
                    logger.info("   No limit pool data found.")
            except Exception as e:
                logger.error(f"   Failed to sync limit pool for {trade_date}: {e}")
                
        # C. 两融信用数据补全 (如果汇总或明细中任意一个缺失，则补全两融)
        margin_total_missing = trade_date in missing_dict.get("ods_margin_total", [])
        margin_detail_missing = trade_date in missing_dict.get("ods_margin_detail", [])
        
        if margin_total_missing or margin_detail_missing:
            logger.info(f"-> Backfilling Margin Data for {trade_date} (Total={margin_total_missing}, Detail={margin_detail_missing})...")
            
            # 1. 补全市场汇总数据
            if margin_total_missing:
                try:
                    total_data = await collector_ts.fetch_margin(trade_date)
                    if total_data:
                        cnt = await StockDAO.save_margin_total(total_data)
                        await StockDAO.update_data_readiness(trade_date, "ods_margin_total", len(total_data))
                        logger.info(f"   Successfully saved {cnt} records to margin total.")
                    else:
                        logger.info("   No margin total data found.")
                    await asyncio.sleep(1.0) # Flow control
                except Exception as e:
                    logger.error(f"   Failed to sync margin total for {trade_date}: {e}")
                    
            # 2. 补全个股明细数据
            if margin_detail_missing:
                try:
                    detail_data = await collector_ts.fetch_margin_detail(trade_date)
                    if detail_data:
                        cnt = await StockDAO.save_margin_detail(detail_data)
                        await StockDAO.update_data_readiness(trade_date, "ods_margin_detail", len(detail_data))
                        logger.info(f"   Successfully saved {cnt} records to margin detail.")
                    else:
                        logger.info("   No margin detail data found.")
                    await asyncio.sleep(1.0) # Flow control
                except Exception as e:
                    logger.error(f"   Failed to sync margin detail for {trade_date}: {e}")
                    
        # D. 行情广度面包线补全 (完全依赖本地 stock_kline_daily，不向 Tushare 发起请求)
        if trade_date in missing_dict.get("ods_market_breadth_daily", []):
            logger.info(f"-> Backfilling ods_market_breadth_daily for {trade_date}...")
            try:
                success = await StockDAO.derive_market_breadth(trade_date)
                if success:
                    await StockDAO.update_data_readiness(trade_date, "ods_market_breadth_daily", 1)
                    logger.info("   Successfully derived and saved market breadth indicators locally.")
                else:
                    logger.warning("   Failed to derive market breadth (possibly missing daily K-line).")
            except Exception as e:
                import traceback
                logger.error(f"   Failed to derive market breadth for {trade_date}: {e}\n{traceback.format_exc()}")
                
    logger.info("\nHistorical backfill process completed! Closing database connections...")
    await DBManager.close_pool()
    logger.info("Database pool closed successfully.")

if __name__ == "__main__":
    asyncio.run(main())
