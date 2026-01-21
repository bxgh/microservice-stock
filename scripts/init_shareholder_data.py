#!/usr/bin/env python3
"""全市场股东数据初始化脚本"""
import asyncio
import httpx
import math
import time
import argparse
from typing import List, Dict

# 配置参数
STOCK_CODES_URL = "http://stock-codes:8000/api/v1/stocks" # 容器内访问
MANAGER_API_URL = "http://localhost:8004/api/v1/shareholders/sync-batch" # 方便本地测试，容器内需改 stock-manager
BATCH_SIZE = 50
MAX_CONCURRENT_BATCHES = 2

async def get_all_a_share_stocks() -> List[str]:
    """获取所有A股代码 (上海+深圳)"""
    print(f"Fetch stock codes from {STOCK_CODES_URL}...")
    try:
        # 获取全部 A股
        # 因为接口一次返回有限，需要循环翻页? 文档说 limit=1000
        # 实测 total ~ 5800, loop fetch
        
        all_codes = []
        skip = 0
        limit = 1000
        # Disable proxies for local connections
        client = httpx.AsyncClient(proxies={})
        
        while True:
            # 外部访问用 localhost:8000, 内部用 stock-codes:8000. 
            # 脚本如果在宿主机运行用 localhost
            url = f"http://localhost:8000/api/v1/stocks?security_type=stock&is_listed=true&limit={limit}&skip={skip}"
            resp = await client.get(url)
            data = resp.json()
            
            items = data.get("items", [])
            if not items:
                break
                
            for item in items:
                # 过滤掉 B股 (根据 exchange 和 code 特征?)
                # 简单起见，这里全量之后再过滤，或者直接信任 API params
                code = item.get("standard_code")
                # 过滤 900/200 这种 B股? 
                if code.startswith("900") or code.startswith("200"): 
                    continue
                all_codes.append(code)
            
            if len(items) < limit:
                break
            
            skip += limit
            print(f"Fetched {len(all_codes)} stocks...")
            
        await client.aclose()
        print(f"Total A-share stocks: {len(all_codes)}")
        return all_codes
        
    except Exception as e:
        print(f"Failed to fetch stock codes: {e}")
        return []

async def sync_batch(client: httpx.AsyncClient, codes: List[str], all_history: bool, batch_id: int):
    """同步一个批次"""
    try:
        print(f"  [Batch {batch_id}] Syncing {len(codes)} stocks...")
        
        start_t = time.time()
        # 宿主机访问 stock-manager 端口 8004
        url = "http://localhost:8004/api/v1/shareholders/sync-batch"
        params = {"all": str(all_history).lower()}
        body = {"codes": codes}
        
        resp = await client.post(url, params=params, json=body, timeout=120.0)
        resp_data = resp.json()
        
        cost = time.time() - start_t
        success = resp_data.get("success", 0)
        failed = resp_data.get("failed", 0)
        
        print(f"  [Batch {batch_id}] Done in {cost:.1f}s. Success: {success}, Failed: {failed}")
        if failed > 0:
            failures = resp_data.get("failures", [])
            print(f"    Failures in batch {batch_id}: {[f['code'] for f in failures]}")
            
    except Exception as e:
        print(f"  [Batch {batch_id}] FAILED: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Shareholder Init Script")
    parser.add_argument("--all", action="store_true", help="Sync full history")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of stocks for testing")
    args = parser.parse_args()
    
    # 1. 获取股票列表
    codes = await get_all_a_share_stocks()
    if not codes:
        return
        
    if args.limit > 0:
        codes = codes[:args.limit]
        print(f"Limit synchronization to first {args.limit} stocks.")

    total_stocks = len(codes)
    total_batches = math.ceil(total_stocks / BATCH_SIZE)
    
    print(f"\nStart syncing {total_stocks} stocks in {total_batches} batches. History={args.all}\n")
    
    # 2. 分批同步
    # 使用 Semaphore 控制并发
    sem = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)
    # Disable proxies
    client = httpx.AsyncClient(timeout=120.0, proxies={})
    
    tasks = []
    
    async def worker(batch_codes, b_id):
        async with sem:
            await sync_batch(client, batch_codes, args.all, b_id)
            # 批次间稍微休息，避免 akshare 封禁
            await asyncio.sleep(1)

    for i in range(total_batches):
        batch_codes = codes[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        task = asyncio.create_task(worker(batch_codes, i+1))
        tasks.append(task)
        
    await asyncio.gather(*tasks)
    
    await client.aclose()
    print("\nAll Done.")

if __name__ == "__main__":
    asyncio.run(main())
