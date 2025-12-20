import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest_asyncio.fixture
async def client():
    from app.services.baostock_service import BaoStockService
    import baostock as bs
    bs.login()
    app.state.baostock_service = BaoStockService()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    bs.logout()

@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_kline_endpoint(client):
    # 贵州茅台
    response = await client.get("/api/v1/history/kline/sh.600519?frequency=d&adjust=2")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "close" in data[0]
        assert "date" in data[0]

@pytest.mark.asyncio
async def test_index_cons(client):
    response = await client.get("/api/v1/index/cons/sz.399300")
    assert response.status_code == 200
    data = response.json()
    assert "constituents" in data
    assert isinstance(data["constituents"], list)
