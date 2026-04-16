from app.utils.database import db
import logging

logger = logging.getLogger("monitor-service.migrations")

async def create_tables():
    """创建监控系统所需的补充表"""
    tables = [
        """
        CREATE TABLE IF NOT EXISTS monitor_market_states (
            trade_date DATE PRIMARY KEY,
            dominant_capital VARCHAR(50) COMMENT '主导资金类型',
            state_score DOUBLE COMMENT '状态综合评分',
            market_state CHAR(1) COMMENT '市场状态 A/B/C/D',
            state_continuity INT DEFAULT 1 COMMENT '状态持续天数',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        """
        CREATE TABLE IF NOT EXISTS monitor_capital_thermometers (
            trade_date DATE,
            capital_type VARCHAR(50),
            z_score DOUBLE COMMENT '250日分位数或标准Z值',
            daily_value DOUBLE COMMENT '原始数值',
            PRIMARY KEY (trade_date, capital_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    ]
    
    await db.connect()
    try:
        for sql in tables:
            await db.execute(sql)
            logger.info("表检查/创建成功")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(create_tables())
