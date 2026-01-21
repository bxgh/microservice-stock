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

@pytest.mark.asyncio
async def test_capital_flow(client):
    response = await client.get("/api/v1/capital_flow/600519")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "main_net_inflow" in data[0]

@pytest.mark.asyncio
async def test_block_trade(client):
    response = await client.get("/api/v1/block_trade/daily")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_margin_data(client):
    response = await client.get("/api/v1/margin/600519")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "financing_balance" in data[0]

@pytest.mark.asyncio
async def test_shareholder_info(client):
    response = await client.get("/api/v1/shareholder/600519")
    assert response.status_code == 200
    data = response.json()
    assert "holder_count_history" in data
    assert "top10_holders" in data

@pytest.mark.asyncio
async def test_dividend_history(client):
    response = await client.get("/api/v1/dividend/600519")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_finance_indicators(client):
    response = await client.get("/api/v1/finance/indicators/600519")
    assert response.status_code == 200
    data = response.json()
    assert "ebitda" in data
    assert "fcf" in data
