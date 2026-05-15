import os
import time
import logging
import httpx
import pymysql
import json
from dotenv import load_dotenv
from datetime import datetime

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/sync_adjust_factors_history.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class AdjustFactorHealer:
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
        self.client = httpx.Client(timeout=30.0)

    def get_all_stocks(self):
        sql = "SELECT ts_code FROM stock_basic_info"
        self.cursor.execute(sql)
        return [row[0] for row in self.cursor.fetchall()]

    def sync_stock(self, ts_code):
        token = os.getenv("TUSHARE_TOKEN")
        payload = {
            "api_name": "adj_factor",
            "token": token,
            "params": {"ts_code": ts_code},
            "fields": "trade_date,adj_factor"
        }
        
        response = self.client.post("http://api.tushare.pro", json=payload)
        data_json = response.json()
        
        if data_json.get('code') != 0:
            logger.error(f"Tushare API error for {ts_code}: {data_json.get('msg')}")
            return 0
            
        items = data_json['data']['items']
        if not items:
            return 0
            
        # items are [ [trade_date, adj_factor], ... ]
        # Sort by trade_date ASC
        items.sort(key=lambda x: x[0])
        
        # 2. Identify Change Points
        change_points = []
        last_factor = None
        
        for trade_date_str, adj_factor in items:
            if adj_factor != last_factor:
                # Value changed
                trade_date = datetime.strptime(trade_date_str, '%Y%m%d').date()
                change_points.append((ts_code, trade_date, float(adj_factor)))
                last_factor = adj_factor
        
        # 3. Batch Upsert into DB
        if change_points:
            sql = """
                REPLACE INTO stock_adjust_factor (ts_code, adjust_date, adjust_factor)
                VALUES (%s, %s, %s)
            """
            self.cursor.executemany(sql, change_points)
            self.conn.commit()
            
        return len(change_points)

    def run(self):
        stocks = self.get_all_stocks()
        total = len(stocks)
        logger.info(f"Starting healing for {total} stocks (HTTPX Mode)...")
        
        start_time = time.time()
        for i, ts_code in enumerate(stocks):
            try:
                change_count = self.sync_stock(ts_code)
                
                if (i + 1) % 20 == 0 or (i + 1) == total:
                    elapsed = time.time() - start_time
                    speed = (i + 1) / elapsed
                    eta = (total - (i + 1)) / speed
                    logger.info(f"Progress: {i+1}/{total} | Speed: {speed:.2f} stocks/s | ETA: {eta/60:.2f} min")
                
                time.sleep(0.4) 
                
            except Exception as e:
                if self.conn:
                    self.conn.rollback()
                logger.error(f"Error healing {ts_code}: {e}")
                time.sleep(5)

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        if self.client:
            self.client.close()

if __name__ == "__main__":
    healer = AdjustFactorHealer()
    try:
        healer.run()
    finally:
        healer.close()
