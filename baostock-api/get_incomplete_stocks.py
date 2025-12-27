import asyncio
from app.utils.database import db

async def get_incomplete_stocks():
    """获取需要补充历史数据的股票列表"""
    await db.connect()
    
    try:
        # 获取所有最早日期晚于2020年的股票（这些可能缺少历史数据）
        query = """
        SELECT code, MIN(trade_date) as min_date, MAX(trade_date) as max_date, COUNT(*) as cnt
        FROM stock_kline_daily
        GROUP BY code
        HAVING MIN(trade_date) > '2020-01-01'
        ORDER BY code
        """
        
        results = await db.execute(query)
        
        print(f"发现 {len(results)} 只股票的数据起始日期晚于2020年:")
        print("-" * 80)
        for row in results:
            code, min_date, max_date, cnt = row
            print(f"{code}: {min_date} ~ {max_date} ({cnt}条记录)")
        
        # 输出为可执行的补录脚本
        print("\n" + "=" * 80)
        print("补录命令:")
        print("=" * 80)
        for row in results:
            code = row[0]
            print(f'curl -X POST "http://localhost:8001/api/v1/sync/kline/{code}?start_date=1990-12-19"')
        
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(get_incomplete_stocks())
