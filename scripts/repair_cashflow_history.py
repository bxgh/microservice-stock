import asyncio
import os
import sys
from dotenv import load_dotenv

# 加载根目录 .env
load_dotenv(".env")

# 将 stock-manager-api 路径加入 sys.path
sys.path.append(os.path.abspath("stock-manager-api"))

# 在 host 环境下运行时，Override 容器内部 URL 为 localhost 映射端口
os.environ["TUSHARE_API_URL"] = "http://localhost:8005"
os.environ["AKSHARE_API_URL"] = "http://localhost:8003"
os.environ["BAOSTOCK_API_URL"] = "http://localhost:8001"
os.environ["PYWENCAI_API_URL"] = "http://localhost:8002"

from app.utils.database import db
from app.services.financial_data_service import FinancialDataService
from app.utils.logger import setup_logger

logger = setup_logger("repair_cashflow_history")

async def get_all_stocks():
    # 只选择已在 ods_fin_cashflow 中有记录但需要修复的股票
    sql = "SELECT DISTINCT ts_code FROM ods_fin_cashflow"
    rows = await db.execute(sql)
    return [row[0] for row in rows]

async def main():
    await db.connect()
    stocks = await get_all_stocks()
    total = len(stocks)
    logger.info(f"开始修复现金流量表数据，共 {total} 只股票")
    
    service = FinancialDataService()
    
    success_count = 0
    error_count = 0
    
    for i, ts_code in enumerate(stocks):
        try:
            if (i + 1) % 50 == 0:
                logger.info(f"进度: [{i+1}/{total}]...")
                
            # 仅同步现金流量表
            count = await service.sync_cashflow(ts_code)
            success_count += 1
            
            # 控制频率，避免 429
            await asyncio.sleep(0.3) 
                
        except Exception as e:
            logger.error(f"修复 {ts_code} 失败: {e}")
            error_count += 1
            
    logger.info(f"修复完成! 成功: {success_count}, 失败: {error_count}")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
