import asyncio
import sys
import os
import pytest
from httpx import AsyncClient, Response

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.main import app
from app.utils.database import db
from app.config import settings

# Override settings for local testing (since test runs outside docker)
settings.DB_HOST = "sh-cdb-h7flpxu4.sql.tencentcdb.com"
settings.DB_PORT = 26300

@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    await db.connect()
    yield
    await db.disconnect()

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "wxch-gateway"}

# To test auth and diary without a real WeChat code, we could mock the service
# But for simplicity, we can just use the DB to get a user and create a token
from app.utils.auth import create_access_token

@pytest.mark.asyncio
async def test_user_profile_and_diary():
    # 1. Get a test user (from initialization script, e.g. dev_openid_001)
    res = await db.execute("SELECT id FROM sys_user WHERE openid = 'dev_openid_001' LIMIT 1")
    if not res:
        pytest.skip("Test user not found, skip tests")
    
    user_id = res[0]["id"]
    token = create_access_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 2. Test User Profile
        profile_res = await ac.get("/api/v1/user/profile", headers=headers)
        assert profile_res.status_code == 200
        profile_data = profile_res.json()
        assert profile_data["id"] == user_id
        
        # 3. Test Diary List
        list_res = await ac.get("/api/v1/diaries/entries", headers=headers)
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert "items" in list_data
        
        # 4. Create Diary
        new_diary = {
            "entry_date": "2026-05-01",
            "entry_type": 5,
            "title": "API Test Diary",
            "content": "This is a test content from API",
            "stocks": ["600519.SH"],
            "tags": ["测试标签"]
        }
        create_res = await ac.post("/api/v1/diaries/entries", json=new_diary, headers=headers)
        assert create_res.status_code == 200, create_res.text
        created_data = create_res.json()
        assert created_data["title"] == new_diary["title"]
        new_id = created_data["id"]
        
        # 5. Get Diary
        get_res = await ac.get(f"/api/v1/diaries/entries/{new_id}", headers=headers)
        assert get_res.status_code == 200
        
        # 6. Delete Diary
        del_res = await ac.delete(f"/api/v1/diaries/entries/{new_id}", headers=headers)
        assert del_res.status_code == 200
        
if __name__ == "__main__":
    asyncio.run(test_health())
