import os
import sys
import asyncio
import logging
import datetime
import pandas as pd
from typing import List, Set, Dict
from dotenv import load_dotenv

# 确保可以导入 shared 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载 .env
load_dotenv("/home/ubuntu/microservice-stock/.env")

# 适配环境变量名
os.environ["MYSQL_HOST"] = os.getenv("DB_HOST", "localhost")
os.environ["MYSQL_PORT"] = os.getenv("DB_PORT", "3306")
os.environ["MYSQL_USER"] = os.getenv("DB_USER", "root")
os.environ["MYSQL_PASSWORD"] = os.getenv("DB_PASSWORD", "")
os.environ["MYSQL_DB"] = os.getenv("DB_NAME", "stock")

from shared.db.connection import DBManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("IntegrityAuditor")

class KlineIntegrityAuditor:
    def __init__(self):
        self.pool = None
        self.trade_days: List[str] = []
        self.stock_basic: pd.DataFrame = None

    async def init_context(self):
        """加载元数据上下文"""
        self.pool = await DBManager.get_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT DISTINCT cal_date FROM trade_cal WHERE is_open=1 ORDER BY cal_date ASC")
                rows = await cur.fetchall()
                self.trade_days = [r[0].strftime('%Y%m%d') if isinstance(r[0], datetime.date) else str(r[0]).replace('-', '') for r in rows]
                
                await cur.execute("SELECT ts_code, name, market, list_status, list_date, delist_date FROM stock_basic_info")
                rows = await cur.fetchall()
                self.stock_basic = pd.DataFrame(rows, columns=['ts_code', 'name', 'market', 'list_status', 'list_date', 'delist_date'])
                self.stock_basic['list_date'] = self.stock_basic['list_date'].apply(lambda x: str(x).replace('-', '') if x else '19000101')
                self.stock_basic['delist_date'] = self.stock_basic['delist_date'].apply(lambda x: str(x).replace('-', '') if x else '20991231')

    def get_theory_stocks(self, date_str: str) -> pd.DataFrame:
        """获取某日理论股票列表 (应用 v2 过滤逻辑)"""
        mask = (self.stock_basic['list_date'] <= date_str) & (self.stock_basic['delist_date'] >= date_str)
        if int(date_str) >= 20250101:
            mask = mask & (self.stock_basic['list_status'] == 'L')
        return self.stock_basic[mask]

    async def analyze_holes(self, target_day: str):
        await self.init_context()
        
        theory_df = self.get_theory_stocks(target_day)
        theory_codes = set(theory_df['ts_code'])
        
        db_day_format = f"{target_day[:4]}-{target_day[4:6]}-{target_day[6:]}"
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT ts_code FROM stock_kline_daily WHERE trade_date = %s", (db_day_format,))
                actual_codes = set([r[0] for r in await cur.fetchall()])
        
        holes = theory_codes - actual_codes
        if not holes:
            print("未发现空洞")
            return
            
        missing_df = theory_df[theory_df['ts_code'].isin(holes)]
        print(f"\n分析日期: {target_day} | 理论: {len(theory_codes)} | 实际: {len(actual_codes)} | 缺失: {len(holes)}")
        
        print("\n--- 缺失个股市场分布 (二轮审计) ---")
        print(missing_df['market'].value_counts())
        
        print("\n--- 缺失个股示例 (二轮审计 - 前 50 只) ---")
        pd.set_option('display.max_rows', 50)
        print(missing_df[['ts_code', 'name', 'market', 'list_date', 'list_status']].head(50))

if __name__ == "__main__":
    auditor = KlineIntegrityAuditor()
    asyncio.run(auditor.analyze_holes("20260515"))
