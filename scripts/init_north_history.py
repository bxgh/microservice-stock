import asyncio
import httpx
from datetime import datetime, timedelta
import sys

API_BASE = "http://localhost:8004/api/v1"

async def get_north_stock_list():
    """获取北向资金持股列表 (用于获取代码清单)"""
    # 尝试获取最近几天的 (由于数据源可能停更，增加 2024-08-16 尝试)
    date = datetime.now().strftime("%Y-%m-%d")
    dates_to_try = [date]
    for i in range(1, 5):
        dates_to_try.append((datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"))
    dates_to_try.append("2024-08-16") # 已知最后更新日期
    
    async with httpx.AsyncClient(timeout=60.0, proxies={}) as client:
        for try_date in dates_to_try:
            print(f"尝试获取北向资金列表: {try_date} ...")
            try:
                url = f"http://localhost:8003/api/v1/north/daily?date={try_date}"
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    if data and len(data) > 100: # Assuming at least 100 stocks
                        print(f"成功获取列表，共 {len(data)} 只股票")
                        return [item['code'] for item in data]
            except Exception as e:
                print(f"获取失败: {e}")
            
    print("无法获取北向资金列表")
    return []

async def sync_history_for_code(client, code):
    url = f"{API_BASE}/game/sync/north/history/{code}"
    try:
        resp = await client.post(url)
        resp.raise_for_status()
        data = resp.json()
        print(f"[{code}] 同步成功: {data.get('synced_count')} 条")
    except Exception as e:
        print(f"[{code}] 同步失败: {e}")

async def main():
    print("开始北向资金历史数据初始化...")
    codes = await get_north_stock_list()
    if not codes:
        return

    print(f"准备同步 {len(codes)} 只股票的历史数据...")
    
    # 并发控制
    sem = asyncio.Semaphore(5) # 5 concurrent requests
    
    async with httpx.AsyncClient(timeout=120.0, proxies={}) as client:
        async def worker(code):
            async with sem:
                await sync_history_for_code(client, code)
        
        tasks = [worker(code) for code in codes]
        # Use simple gather or tqdm?
        # Let's just gather
        # Split into chunks to avoid too many tasks
        chunk_size = 50
        for i in range(0, len(codes), chunk_size):
            chunk = codes[i:i+chunk_size]
            await asyncio.gather(*[worker(c) for c in chunk])
            print(f"进度: {min(i+chunk_size, len(codes))}/{len(codes)}")

if __name__ == "__main__":
    asyncio.run(main())
