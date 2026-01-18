import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8004/api/v1/data-audits"

async def test_data_audit_api():
    async with httpx.AsyncClient() as client:
        # 1. Get List
        print("Testing List API...")
        resp = await client.get(BASE_URL, params={"page": 1, "size": 5})
        if resp.status_code != 200:
            print(f"List API failed: {resp.text}")
            return
        
        data = resp.json()
        print(f"List success. Total: {data['total']}, Items: {len(data['items'])}")
        
        if not data['items']:
            print("No items to test detail API.")
            return

        first_id = data['items'][0]['id']
        
        # 2. Get Detail
        print(f"Testing Detail API for ID {first_id}...")
        resp = await client.get(f"{BASE_URL}/{first_id}")
        if resp.status_code == 200:
            print("Detail API success.")
        else:
            print(f"Detail API failed: {resp.text}")

        # 3. Get Sub-details
        print(f"Testing Sub-details API for ID {first_id}...")
        resp = await client.get(f"{BASE_URL}/{first_id}/details")
        if resp.status_code == 200:
             items = resp.json().get('items', [])
             print(f"Sub-details success. Count: {len(items)}")
        else:
            print(f"Sub-details API failed: {resp.text}")

if __name__ == "__main__":
    # Ensure URL is correct inside container or pass via Env, here assuming localhost accessible 
    # But usually we run this inside the container or network. 
    # For now, just print the script location.
    pass
    # Actual execution needs running service.
    # We will simulate run with run_command if needed.
    # Since I cannot restart the server here, I assume the server is running or will reload.
    # FastAPI uvicorn usually reloads.
    asyncio.run(test_data_audit_api())
