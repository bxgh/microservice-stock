import os
import time
import logging
import pymysql
from dotenv import load_dotenv
from datetime import datetime, date

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/backfill_adj_factor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class Backfiller:
    def __init__(self):
        self.conn = pymysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            charset='utf8mb4',
            autocommit=False
        )
        self.cursor = self.conn.cursor()

    def get_all_ts_codes(self):
        logger.info("Fetching list of all stocks from stock_basic_info...")
        sql = "SELECT ts_code FROM stock_basic_info"
        self.cursor.execute(sql)
        return [row[0] for row in self.cursor.fetchall()]

    def process_stock(self, ts_code):
        # 第一步：forward-fill（只处理当前这只股票）
        # 使用子查询找到每个交易日对应的最新因子
        sql_fill = """
            UPDATE stock_kline_daily k
            SET k.adj_factor = (
                SELECT af.adjust_factor
                FROM stock_adjust_factor af
                WHERE af.ts_code = k.ts_code
                  AND af.adjust_date <= k.trade_date
                ORDER BY af.adjust_date DESC
                LIMIT 1
            )
            WHERE k.ts_code = %s
        """
        self.cursor.execute(sql_fill, (ts_code,))

        # 第二步：IPO 早期补 1.0（针对从未发生过除权的阶段）
        sql_fallback = """
            UPDATE stock_kline_daily
            SET adj_factor = 1.000000
            WHERE ts_code = %s AND adj_factor IS NULL
        """
        self.cursor.execute(sql_fallback, (ts_code,))

    def run(self):
        start_time = time.time()
        ts_codes = self.get_all_ts_codes()
        total = len(ts_codes)
        logger.info(f"Found {total} stocks to process.")

        for i, ts_code in enumerate(ts_codes):
            try:
                self.process_stock(ts_code)
                self.conn.commit()
                
                if (i + 1) % 50 == 0 or (i + 1) == total:
                    elapsed = time.time() - start_time
                    speed = (i + 1) / elapsed
                    eta = (total - (i + 1)) / speed
                    percentage = (i + 1) / total * 100
                    logger.info(f"Progress: {i+1}/{total} ({percentage:.2f}%) | Speed: {speed:.2f} stocks/s | ETA: {eta/60:.2f} min")
            except Exception as e:
                self.conn.rollback()
                logger.error(f"Error processing {ts_code}: {e}")
                # Wait a bit before retry or skip
                time.sleep(1)

        total_time = time.time() - start_time
        logger.info(f"Backfill completed in {total_time/60:.2f} minutes.")

    def close(self):
        self.cursor.close()
        self.conn.close()

if __name__ == "__main__":
    backfiller = Backfiller()
    try:
        backfiller.run()
    finally:
        backfiller.close()
