#!/usr/bin/env python3
"""补全缺失的股东数据 (Host运行)"""
import asyncio
import httpx
import json
import subprocess
import time
import argparse
from typing import Set

# 配置
STOCK_CODES_URL = "http://localhost:8000/api/v1/stocks"
MANAGER_SYNC_URL = "http://localhost:8004/api/v1/shareholders/sync-batch"

async def get_all_stock_codes() -> Set[str]:
    """获取所有A股代码"""
    print("Fetching all stock codes from localhost:8000...")
    all_codes = set()
    skip = 0
    limit = 1000
    
    async with httpx.AsyncClient(proxies={}) as client:
        while True:
            try:
                url = f"{STOCK_CODES_URL}?security_type=stock&is_listed=true&limit={limit}&skip={skip}"
                resp = await client.get(url, timeout=30.0)
                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break
                    
                for item in items:
                    code = item.get("standard_code")
                    if code.startswith("900") or code.startswith("200"): 
                        continue
                    all_codes.add(code)
                
                if len(items) < limit:
                    break
                skip += limit
                print(f"Fetched {len(all_codes)} codes...")
            except Exception as e:
                print(f"Error fetching stocks: {e}")
                return set()
    return all_codes

def get_synced_codes() -> Set[str]:
    """通过 docker exec 获取已同步的代码"""
    print("Fetching synced codes from stock-manager DB...")
    try:
        # 运行容器内的辅助脚本
        # 注意：脚本路径需对应容器内位置
        cmd = ["docker", "exec", "stock-manager", "python", "/app/app/get_synced_codes_json.py"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        output = result.stdout.strip()
        # 输出可能包含 logs，找最后一行 JSON
        lines = output.split('\n')
        json_line = lines[-1]
        
        codes = json.loads(json_line)
        if isinstance(codes, dict) and "error" in codes:
            print(f"DB Error: {codes['error']}")
            return set()
            
        return set(codes)
    except subprocess.CalledProcessError as e:
        print(f"Docker exec failed: {e.stderr}")
        return set()
    except json.JSONDecodeError as e:
        print(f"Failed to parse DB output: {e}")
        return set()

async def sync_batch(client: httpx.AsyncClient, codes: list):
    """批量同步"""
    try:
        resp = await client.post(
            MANAGER_SYNC_URL, 
            params={"all": "true"}, 
            json={"codes": codes},
            timeout=120.0
        )
        data = resp.json()
        return data
    except Exception as e:
        print(f"Sync request failed: {e}")
        return {"success": 0, "failed": len(codes)}

async def main():
    start_time = time.time()
    
    # 1. 获取所有代码
    all_codes = await get_all_stock_codes()
    print(f"Total A-share stocks: {len(all_codes)}")
    
    # 2. 获取已同步代码
    synced_codes = get_synced_codes()
    print(f"Synced stocks: {len(synced_codes)}")
    
    # 3. 计算缺失
    missing = list(all_codes - synced_codes)
    print(f"Missing stocks: {len(missing)}")
    
    if not missing:
        print("All stocks synced!")
        return

    # 4. 批量同步
    batch_size = 20
    total_batches = (len(missing) + batch_size - 1) // batch_size
    print(f"Starting sync for {len(missing)} stocks in {total_batches} batches...\n")
    
    async with httpx.AsyncClient(proxies={}, timeout=120.0) as client:
        for i in range(0, len(missing), batch_size):
            batch = missing[i : i + batch_size]
            b_idx = i // batch_size + 1
            
            print(f"Syncing Batch {b_idx}/{total_batches} ({len(batch)} stocks)...")
            result = await sync_batch(client, batch)
            
            success = result.get("success", 0)
            failed = result.get("failed", 0)
            print(f"  Batch {b_idx} Done. Success: {success}, Failed: {failed}")
            
            if failed > 0:
                print(f"  Failures: {[f['code'] for f in result.get('failures', [])]}")
            
            # 简单限流
            await asyncio.sleep(1)
            
    print(f"\nRetry process completed in {time.time() - start_time:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
