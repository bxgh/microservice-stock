import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest_asyncio.fixture
async def client():
    from app.services.wencai_service import WencaiService
    app.state.wencai_service = WencaiService()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_query_endpoint(client):
    response = await client.post("/api/v1/query", json={"q": "今日涨停", "perpage": 5})
    assert response.status_code in [200, 503]
    if response.status_code == 200:
        data = response.json()
        assert "columns" in data
        assert "data" in data

@pytest.mark.asyncio
async def test_hot_sectors(client):
    response = await client.get("/api/v1/sector/hot?limit=5")
    assert response.status_code in [200, 503]
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)
