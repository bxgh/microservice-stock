import asyncio
import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# 加载根目录 .env
load_dotenv(".env")

# 将 stock-manager-api 路径加入 sys.path
sys.path.append(os.path.abspath("stock-manager-api"))

from app.utils.database import db
from app.services.financial_data_service import FinancialDataService
from app.utils.logger import setup_logger

logger = setup_logger("init_financial_history")

async def get_all_stocks():
    sql = "SELECT ts_code FROM stock_basic_info WHERE list_status = 'L'"
    rows = await db.execute(sql)
    return [row[0] for row in rows]

async def main(start_year: int, end_year: int, batch_size: int = 10):
    stocks = await get_all_stocks()
    total = len(stocks)
    logger.info(f"开始历史财务数据初始化，共 {total} 只股票")
    
    service = FinancialDataService()
    
    # 按照年份区间进行同步（Tushare 接口通常建议按股票+年份拉取以避免数据量过大）
    # 但我们的 sync_all_financial_data 默认拉取该股票的全量或由 period 控制
    # 为了保险，我们一只一只同步，并在每只之间加微小延迟
    
    success_count = 0
    error_count = 0
    
    for i, ts_code in enumerate(stocks):
        try:
            logger.info(f"[{i+1}/{total}] 正在同步 {ts_code}...")
            # 同步该股票的所有历史财务数据
            # 默认 sync_balancesheet 等不传 period 会拉取 Tushare 返回的默认长度（通常是全量或近几年）
            # Tushare 接口如果传了 ts_code 且不传 period，通常返回历史记录
            result = await service.sync_all_financial_data(ts_code)
            
            logger.info(f"同步成功: {ts_code} | BS: {result['balancesheet']} | IS: {result['income']} | CF: {result['cashflow']}")
            success_count += 1
            
            # 控制频率，避免触发 tushare-api 的限流
            if (i + 1) % batch_size == 0:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"同步 {ts_code} 失败: {e}")
            error_count += 1
            
    logger.info(f"初始化完成! 成功: {success_count}, 失败: {error_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="历史财务数据初始化脚本")
    parser.add_argument("--start_year", type=int, default=2010, help="开始年份")
    parser.add_argument("--end_year", type=int, default=datetime.now().year, help="结束年份")
    parser.add_argument("--batch_size", type=int, default=20, help="批次大小")
    
    args = parser.parse_args()
    
    asyncio.run(main(args.start_year, args.end_year, args.batch_size))
