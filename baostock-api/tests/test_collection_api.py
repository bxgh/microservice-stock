
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# MOCK apscheduler before importing app.main
mock_apscheduler = MagicMock()
mock_apscheduler.__path__ = [] # Mark as package
sys.modules["apscheduler"] = mock_apscheduler

# Mock submodules
sys.modules["apscheduler.schedulers"] = MagicMock()
sys.modules["apscheduler.schedulers.asyncio"] = MagicMock()

mock_triggers = MagicMock()
mock_triggers.__path__ = [] # Mark as package
sys.modules["apscheduler.triggers"] = mock_triggers
sys.modules["apscheduler.triggers.cron"] = MagicMock()
sys.modules["apscheduler.triggers.interval"] = MagicMock()

# MOCK aiomysql
mock_aiomysql = MagicMock()
sys.modules["aiomysql"] = mock_aiomysql

# Patch database module to avoid import issues or real connection attempts
# We'll need to patch app.utils.database.db later for specific tests, but this ensures import works
mock_db_module = MagicMock()
mock_db = AsyncMock()
mock_db.execute = AsyncMock() # Ensure execute is awaitable
mock_db.fetch_all = AsyncMock()
mock_db_module.db = mock_db
sys.modules["app.utils.database"] = mock_db_module
from app.utils.database import db # This will be the mock

from fastapi.testclient import TestClient
from app.main import app
from app.services.collection_service import CollectionService

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_baostock_service():
    """Mock BaoStockService to avoid real network calls"""
    mock = AsyncMock()
    # Setup default success response for sync
    mock.sync_kline_to_db.return_value = {
        "success": True,
        "count": 100,
        "performance": {"total_ms": 500}
    }
    return mock

@pytest.fixture
def setup_dependencies(mock_baostock_service):
    """Inject mock services into app.state"""
    collection_service = CollectionService(mock_baostock_service)
    app.state.baostock_service = mock_baostock_service
    app.state.collection_service = collection_service
    return collection_service

def test_submit_collection_task(client, setup_dependencies):
    """Test submitting a new collection task"""
    response = client.post("/api/v1/collect/stock_history", json={
        "stock_code": "sh.600000",
        "start_date": "2020-01-01",
        "clear_existing": True
    })
    
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "task_id" in data
    
    # Check if task is registered in service
    service = setup_dependencies
    task_id = data["task_id"]
    task = service.get_task_status(task_id)
    assert task is not None
    # Background task might have finished already
    assert task["status"] in ["pending", "running", "success"]

def test_get_task_status_not_found(client, setup_dependencies):
    """Test getting status for non-existent task"""
    response = client.get("/api/v1/collect/task/invalid-id")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_run_collection_execution(setup_dependencies, mock_baostock_service):
    """Test the execution logic of CollectionService directly"""
    service = setup_dependencies
    
    # Register a task manually
    task_id = await service.submit_collection_task("sh.600000", "2020-01-01", clear_existing=True)
    
    # Mock DB execute (for delete)
    with patch("app.utils.database.db.execute", new_callable=AsyncMock) as mock_db_exec:
        # Run execution
        await service.run_stock_history_collection(task_id, "sh.600000", "2020-01-01", True)
        
        # Verify DB delete was called
        mock_db_exec.assert_called_once()
        assert "DELETE FROM stock_kline_daily" in mock_db_exec.call_args[0][0]
        
    # Verify Sync was called with correct params
    mock_baostock_service.sync_kline_to_db.assert_called_with(
        code="sh.600000",
        start_date="2020-01-01",
        frequency="d",
        adjust="2",
        use_db_latest=False  # IMPORTANT: Must enforce False
    )
    
    # Check Task Status
    task = service.get_task_status(task_id)
    assert task["status"] == "success"
    assert task["result"]["records_collected"] == 100
