import os
import sys
import asyncio
import logging
import time
import datetime
from typing import List, Dict, Any, Optional

# 1. 路径修复：确保能从 scf-collector/shared 加载模块
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(root_dir, ".env"), override=True)

from shared.collectors.tushare_cl import TushareCollector
from shared.db.dao import StockDAO
from shared.db.connection import DBManager, execute_query

# 配置日志
log_dir = os.path.join(root_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(log_dir, 'tushare_financial_backfill.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger("FinancialBackfill")

# Tushare 2000 积分限制：每只股票拉取 4 个财报接口，单线程执行休眠 1.5s 确保安全，同时防数据库瞬时并发压力
THROTTLE_SLEEP = 1.5
TASK_NAME = 'financial_sheets_backfill'

async def get_listed_stocks() -> List[str]:
    """从数据库获取全市场所有在市的 A 股股票代码"""
    sql = "SELECT ts_code FROM stock_basic_info WHERE list_status = 'L' ORDER BY ts_code ASC"
    rows = await execute_query(sql, is_select=True)
    return [r['ts_code'] for r in rows] if rows else []

def deduplicate_records(data: List[Dict[str, Any]], has_report_type: bool = True) -> List[Dict[str, Any]]:
    """
    [E13-S4-T3] Python 业务层排重与预清洗逻辑
    针对可能存在的更正公告多条重复记录，按唯一键 (end_date, report_type) 对数据进行分组，
    仅保留公告日期 (ann_date 或 f_ann_date) 最新的那条有效记录。
    """
    if not data:
        return []
    
    groups = {}
    for item in data:
        end_date = item.get('end_date')
        if not end_date:
            continue
        
        # 确定唯一键标识
        if has_report_type:
            report_type = item.get('report_type', '1')
            key = (end_date, report_type)
        else:
            key = end_date
            
        ann_date = str(item.get('ann_date', '') or '')
        f_ann = str(item.get('f_ann_date', '') or '')
        # 优先使用实际披露公告日对比时序，否则使用默认公告日
        compare_date = f_ann if f_ann else ann_date
        
        if key not in groups:
            groups[key] = (compare_date, item)
        else:
            saved_date, _ = groups[key]
            if compare_date > saved_date:
                groups[key] = (compare_date, item)
                
    return [val[1] for val in groups.values()]

async def run_backfill():
    """主回填跑批引擎"""
    logger.info(">>> 启动 Tushare 财务三表与指标全量回填同步引擎 (E13-S4-T3) <<<")
    
    collector = TushareCollector()
    if not collector.pro:
        logger.error("TUSHARE_TOKEN 环境变量未配置，同步终止。")
        return

    # 1. 获取目标股票列表
    stocks = await get_listed_stocks()
    total_stocks = len(stocks)
    if total_stocks == 0:
        logger.error("未在 stock_basic_info 表中获取到在市股票代码，请检查基础信息采集状态。")
        return
        
    logger.info(f"全市场在市股票总数: {total_stocks} 支 | 单步流控休眠: {THROTTLE_SLEEP}s")
    
    overall_start_time = time.time()
    
    # 2. 个股循环处理 (实现断点续传)
    for idx, ts_code in enumerate(stocks):
        check_sql = "SELECT status FROM sync_progress WHERE task_name=%s AND current_code=%s"
        res = await execute_query(check_sql, (TASK_NAME, ts_code))
        
        if res and res[0]['status'] == 'completed':
            continue

        start_time = time.time()
        
        # 打印炫酷的 CLI 进度条与 ETA 时间预测
        progress = (idx + 1) / total_stocks
        bar_length = 20
        filled_length = int(round(bar_length * progress))
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        elapsed = time.time() - overall_start_time
        avg_time = elapsed / (idx + 1)
        remaining_stocks = total_stocks - (idx + 1)
        eta_sec = avg_time * remaining_stocks
        eta_str = str(datetime.timedelta(seconds=int(eta_sec)))
        
        sys.stdout.write(f"\r进度: |{bar}| {progress*100:.1f}% [{idx+1}/{total_stocks}] 正在拉取 {ts_code} | ETA: {eta_str}")
        sys.stdout.flush()
        
        try:
            # (1) 抓取资产负债表并保存 (合并报表)
            bs_data = await collector.fetch_balancesheet(ts_code)
            bs_clean = deduplicate_records(bs_data, has_report_type=True)
            if bs_clean:
                await StockDAO.save_balancesheet(bs_clean)
                
            # (2) 抓取利润表并保存 (合并报表)
            inc_data = await collector.fetch_income(ts_code)
            inc_clean = deduplicate_records(inc_data, has_report_type=True)
            if inc_clean:
                await StockDAO.save_income(inc_clean)
                
            # (3) 抓取现金流量表并保存 (合并报表)
            cf_data = await collector.fetch_cashflow(ts_code)
            cf_clean = deduplicate_records(cf_data, has_report_type=True)
            if cf_clean:
                await StockDAO.save_cashflow(cf_clean)
                
            # (4) 抓取财务指标指标表并保存
            ind_data = await collector.fetch_fina_indicator(ts_code)
            ind_clean = deduplicate_records(ind_data, has_report_type=False)
            if ind_clean:
                await StockDAO.save_fina_indicator(ind_clean)

            # (5) 记录个股断点完成进度
            upsert_sql = """
            INSERT INTO sync_progress (task_name, current_code, status, last_index, total_count)
            VALUES (%s, %s, 'completed', %s, %s)
            ON DUPLICATE KEY UPDATE status='completed', last_index=%s, updated_at=CURRENT_TIMESTAMP
            """
            await execute_query(upsert_sql, (TASK_NAME, ts_code, idx + 1, total_stocks, idx + 1))
            
            # [E13-S4-AC1] 强制单步 Throttling 休眠，防止接口限流
            await asyncio.sleep(THROTTLE_SLEEP)
            
        except Exception as e:
            sys.stdout.write("\n")
            logger.error(f"[{idx+1}/{total_stocks}] {ts_code} 同步中途发生报错异常: {e}")
            # 网络抖动或者限流触发，休眠 5 秒后跳过并继续下只股票，防止批量流控拦截中断脚本
            await asyncio.sleep(5)

    sys.stdout.write("\n")
    logger.info(">>> Tushare 历史财务三表与指标全量回填跑批圆满完成！ <<<")

if __name__ == "__main__":
    try:
        asyncio.run(run_backfill())
    except KeyboardInterrupt:
        logger.info("任务被用户手动 KeyboardInterrupt 中断")
    finally:
        # 显式关闭全局数据库连接池以防连接泄漏
        loop = asyncio.get_event_loop()
        loop.run_until_complete(DBManager.close_pool())
