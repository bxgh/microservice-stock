import asyncio
import os
import sys

# Ensure stock-manager-api is in path to import config
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(os.path.join(project_root, 'app'))

try:
    from app.config import settings
except ImportError:
    # Handle path issues if running from different locations
    sys.path.append(project_root)
    from app.config import settings

import aiomysql

async def create_chip_tables():
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
            # 1. 限售解禁表 (stock_restricted_release)
            sql_restricted = """
            CREATE TABLE IF NOT EXISTS `stock_restricted_release` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `ts_code` varchar(20) NOT NULL COMMENT '股票代码',
                `release_date` date NOT NULL COMMENT '解禁日期',
                `release_count` bigint(20) DEFAULT NULL COMMENT '解禁数量',
                `release_market_cap` decimal(20,2) DEFAULT NULL COMMENT '解禁市值',
                `ratio` decimal(10,4) DEFAULT NULL COMMENT '占总股本比例',
                `holder_type` varchar(255) DEFAULT NULL COMMENT '解禁股本类型',
                `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                UNIQUE KEY `uk_code_date` (`ts_code`,`release_date`),
                KEY `idx_ts_code` (`ts_code`),
                KEY `idx_release_date` (`release_date`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='限售股解禁表';
            """
            await cur.execute(sql_restricted)
            print("Table `stock_restricted_release` checked/created.")

            # 2. 大宗交易表 (stock_block_trade)
            sql_block = """
            CREATE TABLE IF NOT EXISTS `stock_block_trade` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `ts_code` varchar(20) NOT NULL COMMENT '股票代码',
                `trade_date` date NOT NULL COMMENT '交易日期',
                `price` decimal(10,4) DEFAULT NULL COMMENT '成交价',
                `volume` bigint(20) DEFAULT NULL COMMENT '成交量',
                `amount` decimal(20,2) DEFAULT NULL COMMENT '成交额',
                `buyer` varchar(255) DEFAULT NULL COMMENT '买方营业部',
                `seller` varchar(255) DEFAULT NULL COMMENT '卖方营业部',
                `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                KEY `idx_ts_code` (`ts_code`),
                KEY `idx_trade_date` (`trade_date`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='大宗交易表';
            """
            # Note: No unique key on block trade because multiple trades can happen for same stock on same day.
            await cur.execute(sql_block)
            print("Table `stock_block_trade` checked/created.")

    pool.close()
    await pool.wait_closed()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(create_chip_tables())
