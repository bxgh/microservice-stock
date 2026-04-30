import asyncio
import sys
import os
import pytest
from httpx import AsyncClient

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.main import app
from app.utils.database import db
from app.config import settings
from app.utils.auth import create_access_token

# Override settings for local testing
settings.DB_HOST = "sh-cdb-h7flpxu4.sql.tencentcdb.com"
settings.DB_PORT = 26300

@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    await db.connect()
    yield
    await db.disconnect()

@pytest.mark.asyncio
async def test_publish_mp_flow():
    # 1. 确保测试用户存在
    res = await db.execute("SELECT id FROM sys_user WHERE openid = 'dev_openid_001' LIMIT 1")
    if not res:
        # 创建测试用户
        user_id = await db.execute_insert(
            "INSERT INTO sys_user (openid, nickname, status) VALUES (%s, %s, %s)",
            ('dev_openid_001', 'TestUser', 1)
        )
    else:
        user_id = res[0]["id"]
        
    # 2. 确保存在 mp_account
    acc_res = await db.execute("SELECT id FROM mp_account WHERE user_id = %s LIMIT 1", (user_id,))
    if not acc_res:
        await db.execute(
            "INSERT INTO mp_account (user_id, mp_appid, status, is_default) VALUES (%s, %s, %s, %s)",
            (user_id, 'wx_test_appid_123', 1, 1)
        )
        
    token = create_access_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 3. 先创建一个日记
        new_diary = {
            "entry_date": "2026-05-01",
            "entry_type": 5,
            "title": "Publish Test Diary",
            "content": "# Test Header\nThis is a test content for WeChat publishing.",
            "stocks": ["000001.SZ"]
        }
        create_res = await ac.post("/api/v1/diaries", json=new_diary, headers=headers)
        assert create_res.status_code == 200
        diary_id = create_res.json()["id"]
        
        # 4. 调用发布接口
        publish_data = {
            "entry_id": diary_id,
            "is_snapshot": True
        }
        pub_res = await ac.post("/api/v1/diaries/publish/mp", json=publish_data, headers=headers)
        
        assert pub_res.status_code == 200, pub_res.text
        data = pub_res.json()
        assert "publish_record_id" in data
        assert data["wx_media_id"].startswith("mock_media_id_")
        
        # 5. 验证数据库中的记录
        record_id = data["publish_record_id"]
        db_res = await db.execute("SELECT * FROM mp_publish_record WHERE id = %s", (record_id,))
        assert len(db_res) == 1
        assert db_res[0]["diary_id"] == diary_id
        assert db_res[0]["status"] == 1
        # The markdown library might add ids to headers
        assert "Test Header</h1>" in db_res[0]["content_html"]

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
