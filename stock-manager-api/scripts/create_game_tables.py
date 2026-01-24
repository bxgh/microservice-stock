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

async def create_game_tables():
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
            # 1. 龙虎榜每日明细 (stock_lhb_daily)
            sql_lhb = """
            CREATE TABLE IF NOT EXISTS `stock_lhb_daily` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `ts_code` varchar(20) NOT NULL COMMENT '股票代码',
                `trade_date` date NOT NULL COMMENT '交易日期',
                
                `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
                `change_pct` decimal(10,4) DEFAULT NULL COMMENT '涨跌幅',
                `turnover_rate` decimal(10,4) DEFAULT NULL COMMENT '换手率',
                
                `net_buy_amt` decimal(20,2) DEFAULT NULL COMMENT '龙虎榜净买入额',
                `buy_amt` decimal(20,2) DEFAULT NULL COMMENT '龙虎榜买入额',
                `sell_amt` decimal(20,2) DEFAULT NULL COMMENT '龙虎榜卖出额',
                `turnover_amt` decimal(20,2) DEFAULT NULL COMMENT '龙虎榜成交额',
                
                `reason` text DEFAULT NULL COMMENT '上榜原因',
                
                -- 机构数据 (可能为空)
                `inst_net_buy_amt` decimal(20,2) DEFAULT NULL COMMENT '机构净买入额',
                `inst_buy_amt` decimal(20,2) DEFAULT NULL COMMENT '机构买入额',
                `inst_sell_amt` decimal(20,2) DEFAULT NULL COMMENT '机构卖出额',
                `inst_buy_count` int(11) DEFAULT NULL COMMENT '买入机构数',
                `inst_sell_count` int(11) DEFAULT NULL COMMENT '卖出机构数',
                
                `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                UNIQUE KEY `uk_code_date` (`ts_code`,`trade_date`), -- 假设每日每股只有一条汇总记录
                KEY `idx_trade_date` (`trade_date`),
                KEY `idx_ts_code` (`ts_code`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='龙虎榜每日明细表';
            """
            await cur.execute(sql_lhb)
            print("Table `stock_lhb_daily` checked/created.")

            # 2. 北向资金每日持股 (stock_north_funds_daily)
            sql_north = """
            CREATE TABLE IF NOT EXISTS `stock_north_funds_daily` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `ts_code` varchar(20) NOT NULL COMMENT '股票代码',
                `trade_date` date NOT NULL COMMENT '交易日期',
                
                `hold_count` bigint(20) DEFAULT NULL COMMENT '持股数量',
                `hold_market_cap` decimal(20,2) DEFAULT NULL COMMENT '持股市值',
                `hold_ratio` decimal(10,4) DEFAULT NULL COMMENT '持股占比(%)',
                
                `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                UNIQUE KEY `uk_code_date` (`ts_code`,`trade_date`),
                KEY `idx_trade_date` (`trade_date`),
                KEY `idx_ts_code` (`ts_code`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='北向资金每日持股表';
            """
            await cur.execute(sql_north)
            print("Table `stock_north_funds_daily` checked/created.")

    pool.close()
    await pool.wait_closed()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(create_game_tables())
