import asyncio
import aiomysql
from app.config import settings

async def check():
    conn = await aiomysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        db=settings.DB_NAME
    )
    async with conn.cursor() as cur:
        print("Finding specific duplicates for 2024-12-02...")
        sql = """
        SELECT ts_code, trade_date 
        FROM stock_kline_daily 
        WHERE trade_date = '2024-12-02' 
        AND ts_code IN (
            SELECT ts_code 
            FROM stock_kline_daily 
            WHERE trade_date = '2024-12-02' 
            GROUP BY ts_code 
            HAVING COUNT(*) > 1
        ) 
        ORDER BY ts_code
        """
        await cur.execute(sql)
        res = await cur.fetchall()
        for row in res:
            print(row)
    conn.close()

if __name__ == "__main__":
    asyncio.run(check())
