import asyncio
import httpx
from datetime import datetime, timedelta
import sys

# API 端点配置
CHIPS_API_URL = "http://localhost:8004/api/v1/chips"

async def sync_restricted_history():
    print("开始同步限售解禁历史数据...")
    # 分段同步，避免超时或内存溢出
    # AkShare 接口对大范围支持不错，我们分 3 段
    ranges = [
        ("2005-01-01", "2015-12-31"),
        ("2016-01-01", "2022-12-31"),
        ("2023-01-01", "2026-12-31")
    ]
    
    async with httpx.AsyncClient(timeout=300.0, proxies={}) as client:
        for start, end in ranges:
            print(f"  正在同步: {start} -> {end} ...")
            try:
                url = f"{CHIPS_API_URL}/sync/restricted"
                response = await client.post(url, params={"start_date": start, "end_date": end})
                response.raise_for_status()
                res_data = response.json()
                print(f"  成功: 同步了 {res_data.get('synced_count', 0)} 条记录")
            except Exception as e:
                print(f"  失败: {start} -> {end}, 错误: {e}")

async def sync_block_trade_history(start_year=2010):
    print(f"开始同步大宗交易历史数据 (从 {start_year} 年开始)...")
    current_year = datetime.now().year
    
    async with httpx.AsyncClient(timeout=300.0, proxies={}) as client:
        for year in range(start_year, current_year + 1):
            print(f"  正在同步 {year} 年数据...")
            # 大宗交易东财接口有 5000 条限制，按季度同步可能会超出
            # 改为按月同步
            for month in range(1, 13):
                start = f"{year}-{month:02d}-01"
                # 计算下个月的第一天再减一天得到本月最后一天
                if month == 12:
                    end = f"{year}-12-31"
                else:
                    end = (datetime(year, month + 1, 1) - timedelta(days=1)).strftime("%Y-%m-%d")
                
                # 如果是未来日期则跳过
                if start > datetime.now().strftime("%Y-%m-%d"):
                    continue
                # 如果结束日期超过今天，截断到今天
                if end > datetime.now().strftime("%Y-%m-%d"):
                    end = datetime.now().strftime("%Y-%m-%d")
                
                print(f"    月份同步: {start} -> {end} ...")
                try:
                    url = f"{CHIPS_API_URL}/sync/block_trade"
                    response = await client.post(url, params={"start_date": start, "end_date": end})
                    response.raise_for_status()
                    res_data = response.json()
                    print(f"    成功: 同步了 {res_data.get('synced_count', 0)} 条记录")
                except Exception as e:
                    print(f"    失败: {start} -> {end}, 错误: {e}")

async def main():
    # 1. 同步限售解禁
    await sync_restricted_history()
    
    # 2. 同步大宗交易 (默认从 2018 年开始，避免数据量过大导致初次运行太慢，用户可自行调整)
    # 如果用户确实需要所有历史，建议从 2010 年开始
    start_year = 2010
    if len(sys.argv) > 1:
        try:
            start_year = int(sys.argv[1])
        except:
            pass
            
    await sync_block_trade_history(start_year)
    print("所有历史数据同步任务完成。")

if __name__ == "__main__":
    asyncio.run(main())
