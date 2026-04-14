
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
    
    # Drop previous THS table if empty (it is)
    async with conn.cursor() as cur:
        try:
            await cur.execute("DROP TABLE IF EXISTS `stock_industry_ths`")
            print("Dropped stock_industry_ths")
        except Exception as e:
            print(f"Drop failed: {e}")
    
    sql = """
    CREATE TABLE IF NOT EXISTS `stock_industry_em` (
      `id` int AUTO_INCREMENT,
      `ts_code` varchar(20) NOT NULL COMMENT '股票代码 (如 600519.SH)',
      `industry_code` varchar(20) NOT NULL COMMENT '东方财富行业代码 (如 BK0473)',
      `industry_name` varchar(50) NOT NULL COMMENT '东方财富行业名称 (如 半导体)',
      `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_code_ind` (`ts_code`, `industry_code`),
      KEY `idx_code` (`ts_code`),
      KEY `idx_ind_code` (`industry_code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='东方财富行业分类表';
    """
    
    async with conn.cursor() as cur:
        await cur.execute(sql)
        print("Created table stock_industry_em")
        
    conn.close()

if __name__ == "__main__":
    asyncio.run(create_table())
