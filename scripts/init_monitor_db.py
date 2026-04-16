import asyncio
import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

async def init_db():
    conn = await aiomysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        autocommit=True
    )
    
    async with conn.cursor() as cur:
        # 1. 原始大盘统计表
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_market_stats (
                trade_date DATE PRIMARY KEY,
                advance_count INT COMMENT '上涨家数',
                decline_count INT COMMENT '下跌家数',
                total_market_cap DECIMAL(20,2) COMMENT '全市场总市值',
                avg_turnover DECIMAL(10,4) COMMENT '平均换手率',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        # 2. 原始行业/ETF日线表
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_sector_daily (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ts_code VARCHAR(20) NOT NULL COMMENT '行业代码或ETF代码',
                trade_date DATE NOT NULL,
                open DECIMAL(16,4),
                high DECIMAL(16,4),
                low DECIMAL(16,4),
                close DECIMAL(16,4),
                volume DECIMAL(20,2),
                amount DECIMAL(20,2),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_code_date (ts_code, trade_date),
                INDEX idx_date (trade_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        # 3. 原始资金流向汇总表
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_capital_flow_summary (
                trade_date DATE PRIMARY KEY,
                north_net_inflow DECIMAL(20,2) COMMENT '北向资金当日净流入(元)',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        # 4. 监控指标时序结果表
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS monitor_indicators_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                trade_date DATE NOT NULL,
                indicator_key VARCHAR(50) NOT NULL COMMENT '指标标识,如 sector_dispersion',
                indicator_value DECIMAL(16,6) NOT NULL,
                status VARCHAR(10) COMMENT 'green, yellow, red',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_date_key (trade_date, indicator_key)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        # 5. 综合健康度得分表
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS monitor_health_scores (
                trade_date DATE PRIMARY KEY,
                total_score DECIMAL(10,2) NOT NULL,
                risk_level VARCHAR(20) COMMENT '低风险, 中风险, 高风险',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        print("MySQL tables for Structural Bull Monitor created successfully.")

    conn.close()

if __name__ == "__main__":
    asyncio.run(init_db())
