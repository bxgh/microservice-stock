import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration from .env
DB_HOST = os.getenv("DB_HOST", "sh-cdb-h7flpxu4.sql.tencentcdb.com")
DB_PORT = int(os.getenv("DB_PORT", 26300))
DB_NAME = os.getenv("DB_NAME", "alwaysup")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "alwaysup@888")

DDL = """
CREATE TABLE IF NOT EXISTS `stock_finance_indicators` (
  `id` bigint AUTO_INCREMENT PRIMARY KEY,
  `ts_code` varchar(20) NOT NULL COMMENT '股票代码 (如 600519.SH)',
  `report_date` date NOT NULL COMMENT '报告期日期',
  `roe` decimal(20,4) COMMENT '净资产收益率 (%)',
  `roa` decimal(20,4) COMMENT '总资产收益率 (%)',
  `netprofit_margin` decimal(20,4) COMMENT '销售净利率 (%)',
  `grossprofit_margin` decimal(20,4) COMMENT '销售毛利率 (%)',
  `asset_liab_ratio` decimal(20,4) COMMENT '资产负债率 (%)',
  `current_ratio` decimal(20,4) COMMENT '流动比率',
  `eps` decimal(20,4) COMMENT '基本每股收益 (元)',
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_code_date` (`ts_code`, `report_date`)
) COMMENT='个股财务衍生指标表';
"""

def init_table():
    print(f"Connecting to {DB_HOST}:{DB_PORT} as {DB_USER}...")
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection:
            with connection.cursor() as cursor:
                print(f"Executing DDL for stock_finance_indicators...")
                cursor.execute(DDL)
            connection.commit()
            print("Table stock_finance_indicators created successfully.")
            
    except Exception as e:
        print(f"Error initializing table: {e}")

if __name__ == "__main__":
    init_table()
