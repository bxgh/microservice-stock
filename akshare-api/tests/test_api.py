import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest_asyncio.fixture
async def client():
    from app.services.akshare_service import AkShareService
    app.state.akshare_service = AkShareService()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_finance_endpoint(client):
    # 贵州茅台
    response = await client.get("/api/v1/finance/600519")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        assert "total_revenue" in data
        assert "net_profit" in data
        assert "code" in data

@pytest.mark.asyncio
async def test_valuation_endpoint(client):
    response = await client.get("/api/v1/valuation/600519")
    assert response.status_code == 200
    data = response.json()
    assert "pe" in data
    assert "price" in data

@pytest.mark.asyncio
async def test_rank_hot(client):
    response = await client.get("/api/v1/rank/hot?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "rank" in data[0]
