
import asyncio
import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

async def create_table():
    conn = await aiomysql.connect(
        host=os.getenv("DB_HOST", "124.221.80.250"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        autocommit=True
    )
    
    # Drop old table to recreate with new schema
    async with conn.cursor() as cur:
        await cur.execute("DROP TABLE IF EXISTS `stock_industry_ths`")
        print("Dropped old stock_industry_ths table")

    sql = """
    CREATE TABLE IF NOT EXISTS `stock_industry_ths` (
      `id` int AUTO_INCREMENT,
      `ts_code` varchar(20) NOT NULL COMMENT '股票代码 (如 600519.SH)',
      `l1_name` varchar(50) DEFAULT NULL COMMENT '同花顺一级行业',
      `l2_name` varchar(50) DEFAULT NULL COMMENT '同花顺二级行业',
      `l3_name` varchar(50) DEFAULT NULL COMMENT '同花顺三级行业',
      `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_code` (`ts_code`),
      KEY `idx_l1` (`l1_name`),
      KEY `idx_l2` (`l2_name`),
      KEY `idx_l3` (`l3_name`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='同花顺行业分类表 (L1/L2/L3)';
    """
    
    async with conn.cursor() as cur:
        await cur.execute(sql)
        print("Created table stock_industry_ths")
        
    conn.close()

if __name__ == "__main__":
    asyncio.run(create_table())
