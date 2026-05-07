
import httpx
import asyncio
import sys

async def test_api():
    base_url = "http://127.0.0.1:8004/api/v1/pipelines"
    
    print(f"Testing {base_url}/runs...")
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            # 1. Test List Runs
            resp = await client.get(f"{base_url}/runs", params={"limit": 5})
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"Response: {resp.json()}")
            else:
                print(f"Error: {resp.text}")
                
            # 2. Test Stats
            import datetime
            today = datetime.date.today().isoformat()
            print(f"\nTesting {base_url}/stats for {today}...")
            resp = await client.get(f"{base_url}/stats", params={"biz_date": today})
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"Response: {resp.json()}")
            else:
                print(f"Error: {resp.text}")
                
        except Exception as e:
            print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())
