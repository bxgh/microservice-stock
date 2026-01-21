import asyncio
import os
import sys

# Add parent dir to path to allow importing 'app'
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from app.config import settings
except ImportError:
    # If running from inside 'stock-manager-api' root
    sys.path.insert(0, os.getcwd())
    from app.config import settings

import aiomysql

async def create_shareholder_tables():
    print(f"Connecting to database {settings.DB_NAME} at {settings.DB_HOST}:{settings.DB_PORT}...")
    
    try:
        pool = await aiomysql.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            db=settings.DB_NAME,
            autocommit=True
        )
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # 1. 股东户数表 (stock_shareholder_count)
            sql_count = """
            CREATE TABLE IF NOT EXISTS `stock_shareholder_count` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `ts_code` varchar(20) NOT NULL COMMENT '股票代码',
                `end_date` date NOT NULL COMMENT '截止日期',
                `holder_count` int(11) DEFAULT NULL COMMENT '股东户数',
                `holder_change_pct` decimal(10,4) DEFAULT NULL COMMENT '户数变动比例',
                `avg_market_cap` decimal(20,2) DEFAULT NULL COMMENT '户均持股市值',
                `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                UNIQUE KEY `uk_code_date` (`ts_code`,`end_date`),
                KEY `idx_ts_code` (`ts_code`),
                KEY `idx_end_date` (`end_date`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股东户数历史表';
            """
            await cur.execute(sql_count)
            print("Table `stock_shareholder_count` checked/created.")

            # 2. 前十大股东表 (stock_top10_shareholders)
            sql_top10 = """
            CREATE TABLE IF NOT EXISTS `stock_top10_shareholders` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `ts_code` varchar(20) NOT NULL COMMENT '股票代码',
                `end_date` date NOT NULL COMMENT '截止日期',
                `rank` int(11) NOT NULL COMMENT '排名',
                `holder_name` varchar(255) DEFAULT NULL COMMENT '股东名称',
                `share_type` varchar(50) DEFAULT NULL COMMENT '股份类型',
                `hold_count` bigint(20) DEFAULT NULL COMMENT '持股数量',
                `hold_pct` decimal(10,4) DEFAULT NULL COMMENT '持股比例',
                `change_stat` varchar(50) DEFAULT NULL COMMENT '变动状态',
                `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                UNIQUE KEY `uk_code_date_rank` (`ts_code`,`end_date`,`rank`),
                KEY `idx_ts_code` (`ts_code`),
                KEY `idx_holder_name` (`holder_name`(20))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='前十大股东表';
            """
            await cur.execute(sql_top10)
            print("Table `stock_top10_shareholders` checked/created.")

    pool.close()
    await pool.wait_closed()
    print("Done.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_shareholder_tables())
