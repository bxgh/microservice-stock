
import pymysql
import os

# Database Configuration (Hardcoded for script simplicity based on .env)
DB_HOST = "sh-cdb-h7flpxu4.sql.tencentcdb.com"
DB_PORT = 26300
DB_NAME = "alwaysup"
DB_USER = "root"
DB_PASSWORD = "alwaysup@888"

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS `stock_analyst_rank` (
      `id` int AUTO_INCREMENT PRIMARY KEY,
      `stock_code` varchar(20) NOT NULL COMMENT '标准代码 600519.SH',
      `report_date` date NOT NULL,
      `analyst` varchar(50) NOT NULL COMMENT '机构/分析师名称',
      `rating` varchar(20) NOT NULL COMMENT '评级 (买入/增持/中性)',
      `change_direction` varchar(10) COMMENT '变动 (维持/调高/调低)',
      `target_price` decimal(10,2) COMMENT '目标价',
      `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
      UNIQUE KEY `uk_code_date_analyst` (`stock_code`, `report_date`, `analyst`)
    ) COMMENT='机构评级记录表';
    """,
    """
    CREATE TABLE IF NOT EXISTS `stock_performance_forecast` (
      `id` int AUTO_INCREMENT PRIMARY KEY,
      `stock_code` varchar(20) NOT NULL,
      `notice_date` date NOT NULL COMMENT '公告日',
      `report_period` date NOT NULL COMMENT '报告期 (如 2025-12-31)',
      `type` varchar(20) COMMENT '类型 (预增/扭亏/预减)',
      `growth_min` decimal(10,2) COMMENT '增长下限(%)',
      `growth_max` decimal(10,2) COMMENT '增长上限(%)',
      UNIQUE KEY `uk_code_period` (`stock_code`, `report_period`)
    ) COMMENT='业绩预告表';
    """,
    """
    CREATE TABLE IF NOT EXISTS `stock_sentiment_daily` (
      `id` int AUTO_INCREMENT PRIMARY KEY,
      `stock_code` varchar(20) NOT NULL,
      `trade_date` date NOT NULL,
      `post_count` int DEFAULT 0 COMMENT '当日发帖数',
      `read_count` int DEFAULT 0 COMMENT '当日阅读数',
      `comment_count` int DEFAULT 0 COMMENT '当日评论数',
      `rank_score` int DEFAULT 0 COMMENT '股吧热度排名(如有)',
      UNIQUE KEY `uk_code_date` (`stock_code`, `trade_date`)
    ) COMMENT='每日市场热度统计';
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
                    print(f"Executing DDL for table...")
                    cursor.execute(sql)
            connection.commit()
            print("All tables initialized successfully.")
            
    except Exception as e:
        print(f"Error initializing tables: {e}")

if __name__ == "__main__":
    init_tables()
