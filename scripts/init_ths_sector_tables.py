
import asyncio
import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

async def create_tables():
    conn = await aiomysql.connect(
        host=os.getenv("DB_HOST", "124.221.80.250"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        autocommit=True
    )
    
    # 1. 板块字典表
    sql_sector = """
    CREATE TABLE IF NOT EXISTS `stock_sector_ths` (
      `id` INT AUTO_INCREMENT,
      `sector_name` VARCHAR(50) NOT NULL COMMENT '板块名称',
      `sector_type` ENUM('industry', 'concept') NOT NULL COMMENT '板块类型',
      `sector_level` VARCHAR(10) DEFAULT NULL COMMENT '级别 (仅限行业: L1/L2/L3)',
      `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_name_type` (`sector_name`, `sector_type`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='同花顺板块字典';
    """

    # 2. 板块成分表 (针对概念等一对多关系)
    sql_cons = """
    CREATE TABLE IF NOT EXISTS `stock_sector_cons_ths` (
      `id` INT AUTO_INCREMENT,
      `ts_code` VARCHAR(20) NOT NULL COMMENT '股票代码',
      `sector_id` INT NOT NULL COMMENT '板块ID',
      `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_code_sector` (`ts_code`, `sector_id`),
      KEY `idx_code` (`ts_code`),
      KEY `idx_sector` (`sector_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='同花顺板块成分映射';
    """
    
    async with conn.cursor() as cur:
        await cur.execute(sql_sector)
        print("Created table stock_sector_ths")
        await cur.execute(sql_cons)
        print("Created table stock_sector_cons_ths")
        
    conn.close()

if __name__ == "__main__":
    asyncio.run(create_tables())
