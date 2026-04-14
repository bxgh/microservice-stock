
from fastapi import APIRouter, BackgroundTasks
from app.services.metadata_service import MetadataService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

metadata_service = MetadataService()

@router.post("/metadata/sync/stock-list")
async def sync_stock_list(background_tasks: BackgroundTasks):
    """Trigger background sync for Full Stock List (stock_basic_info)"""
    background_tasks.add_task(metadata_service.sync_stock_list)
    return {"status": "accepted", "message": "Stock List Sync started in background"}

@router.post("/metadata/sync/issue-prices")
async def sync_issue_prices(background_tasks: BackgroundTasks):
    """Trigger background sync for Issue Prices (Emission Price)"""
    background_tasks.add_task(metadata_service.sync_issue_prices)
    return {"status": "accepted", "message": "Issue Price Sync started in background"}

@router.post("/metadata/sync/sw-industries")
async def sync_sw_industries(background_tasks: BackgroundTasks):
    """Trigger background sync for Shenwan Level 1/2/3 Industries"""
    background_tasks.add_task(metadata_service.sync_shenwan_industries)
    return {"status": "accepted", "message": "Shenwan Industry Sync started in background"}

@router.post("/metadata/sync/em-industries")
async def sync_em_industries(background_tasks: BackgroundTasks):
    """Trigger background sync for EastMoney Industries"""
    background_tasks.add_task(metadata_service.sync_em_industries)
    return {"status": "accepted", "message": "EastMoney Industry Sync started in background"}

@router.post("/metadata/sync/ths-industries")
async def sync_ths_industries(background_tasks: BackgroundTasks, mode: str = "standard"):
    """Trigger background sync for THS Industries (via Wencai)
    
    Args:
        mode: "standard" (two-phase, default) or "fast" (single query, backup)
    """
    background_tasks.add_task(metadata_service.sync_ths_industries, mode=mode)
    return {"status": "accepted", "message": f"THS Industry Sync ({mode}) started in background"}

@router.post("/metadata/sync/all")
async def sync_all_data(background_tasks: BackgroundTasks, include_heavy: bool = False):
    """手动触发全量数据补全 (Manual Full Sync)
    
    Trigger a comprehensive data update:
    1. Stock List (Basic)
    2. SW Industries & Issue Prices (Metadata)
    3. Market Data (LHB, North Funds)
    4. Sentiment Data (Hot Rank, Suspension)
    5. Restricted Release (Next 30 days)
    
    Args:
        include_heavy: If True, also trigger THS Sector Sync (Time consuming!)
    """
    from app.scheduler import jobs as scheduler_jobs
    
    # 1. Basic & Metadata
    background_tasks.add_task(scheduler_jobs.weekly_stock_list_sync_job)
    background_tasks.add_task(scheduler_jobs.weekly_metadata_sync_job)
    
    # 2. Market & Sentiment
    background_tasks.add_task(scheduler_jobs.daily_market_data_sync_job)
    background_tasks.add_task(scheduler_jobs.daily_sentiment_sync_job)
    
    # 3. Future Events
    background_tasks.add_task(scheduler_jobs.weekly_restricted_release_job)
    
    msg = "Full Data Supplement started: StockList, Metadata, Market, Sentiment, Restricted"
    
    # 4. Heavy Tasks
    if include_heavy:
        background_tasks.add_task(scheduler_jobs.weekly_ths_sector_sync_job)
        msg += ", THS Sectors"
        
    return {"status": "accepted", "message": msg}
