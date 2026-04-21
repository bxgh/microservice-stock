
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

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS `stock_balance_sheet` (
      `id` bigint AUTO_INCREMENT PRIMARY KEY,
      `ts_code` varchar(20) NOT NULL COMMENT '股票代码 600519.SH',
      `report_date` date NOT NULL COMMENT '报告期日期 (如 2023-12-31)',
      `notice_date` date COMMENT '公告日期',
      `total_assets` decimal(20,4) COMMENT '资产总计',
      `total_liabilities` decimal(20,4) COMMENT '负债合计',
      `total_equity` decimal(20,4) COMMENT '所有者权益合计',
      `total_equity_ato_parent` decimal(20,4) COMMENT '归属于母公司股东权益合计',
      `monetary_funds` decimal(20,4) COMMENT '货币资金',
      `accounts_receivable` decimal(20,4) COMMENT '应收账款',
      `notes_receivable` decimal(20,4) COMMENT '应收票据',
      `inventory` decimal(20,4) COMMENT '存货',
      `goodwill` decimal(20,4) COMMENT '商誉',
      `short_term_borrowings` decimal(20,4) COMMENT '短期借款',
      `long_term_borrowings` decimal(20,4) COMMENT '长期借款',
      `total_non_current_assets` decimal(20,4) COMMENT '非流动资产合计',
      `total_current_assets` decimal(20,4) COMMENT '流动资产合计',
      `total_non_current_liabilities` decimal(20,4) COMMENT '非流动负债合计',
      `total_current_liabilities` decimal(20,4) COMMENT '流动负债合计',
      `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
      `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY `uk_code_date` (`ts_code`, `report_date`)
    ) COMMENT='资产负债表';
    """,
    """
    CREATE TABLE IF NOT EXISTS `stock_income_statement` (
      `id` bigint AUTO_INCREMENT PRIMARY KEY,
      `ts_code` varchar(20) NOT NULL,
      `report_date` date NOT NULL,
      `notice_date` date,
      `total_revenue` decimal(20,4) COMMENT '营业总收入',
      `operating_revenue` decimal(20,4) COMMENT '营业收入',
      `total_operating_cost` decimal(20,4) COMMENT '营业总成本',
      `operating_cost` decimal(20,4) COMMENT '营业成本',
      `selling_expenses` decimal(20,4) COMMENT '销售费用',
      `administrative_expenses` decimal(20,4) COMMENT '管理费用',
      `financial_expenses` decimal(20,4) COMMENT '财务费用',
      `research_expenses` decimal(20,4) COMMENT '研发费用',
      `operating_profit` decimal(20,4) COMMENT '营业利润',
      `total_profit` decimal(20,4) COMMENT '利润总额',
      `net_profit` decimal(20,4) COMMENT '净利润',
      `parent_net_profit` decimal(20,4) COMMENT '归属于母公司所有者的净利润',
      `deducted_net_profit` decimal(20,4) COMMENT '扣除非经常性损益后的净利润',
      `ebit` decimal(20,4) COMMENT '息税前利润 (计算得)',
      `ebitda` decimal(20,4) COMMENT '息税折旧摊销前利润 (计算得)',
      `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
      `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY `uk_code_date` (`ts_code`, `report_date`)
    ) COMMENT='利润表';
    """,
    """
    CREATE TABLE IF NOT EXISTS `stock_cash_flow_statement` (
      `id` bigint AUTO_INCREMENT PRIMARY KEY,
      `ts_code` varchar(20) NOT NULL,
      `report_date` date NOT NULL,
      `notice_date` date,
      `net_operating_cash_flow` decimal(20,4) COMMENT '经营活动产生的现金流量净额',
      `net_investing_cash_flow` decimal(20,4) COMMENT '投资活动产生的现金流量净额',
      `net_financing_cash_flow` decimal(20,4) COMMENT '筹资活动产生的现金流量净额',
      `capex` decimal(20,4) COMMENT '购建固定资产、无形资产和其他长期资产支付的现金',
      `free_cash_flow` decimal(20,4) COMMENT '自由现金流 (计算得 OCF-CAPEX)',
      `cash_and_equivalents_at_end` decimal(20,4) COMMENT '期末现金及现金等价物余额',
      `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
      `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY `uk_code_date` (`ts_code`, `report_date`)
    ) COMMENT='现金流量表';
    """
]

def init_tables():
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
                for sql in DDL_STATEMENTS:
                    print(f"Executing DDL...")
                    cursor.execute(sql)
            connection.commit()
            print("Financial tables initialized successfully.")
            
    except Exception as e:
        print(f"Error initializing tables: {e}")

if __name__ == "__main__":
    init_tables()
