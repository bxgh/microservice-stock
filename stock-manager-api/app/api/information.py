from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Query
from app.services.information_service import InformationService
from app.schemas.information import (
    AnalystRankCreate, AnalystRankResponse,
    PerformanceForecastCreate, PerformanceForecastResponse,
    SentimentDailyCreate, SentimentDailyResponse,
    SyncResult
)
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("stock-manager.api.information")

# -----------------------------------------------------------------------------
# Analyst Ranks
# -----------------------------------------------------------------------------
@router.post("/analyst-ranks/sync", response_model=SyncResult)
async def sync_analyst_ranks(request: Request, items: List[AnalystRankCreate]):
    """同步机构评级数据"""
    service = InformationService()
    try:
        count = await service.sync_analyst_ranks([item.model_dump() for item in items])
        return SyncResult(total=len(items), success=count)
    except Exception as e:
        logger.error(f"Failed to sync analyst ranks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analyst-ranks/{ts_code}", response_model=List[AnalystRankResponse])
async def get_analyst_ranks(ts_code: str, limit: int = 50):
    """查询机构评级历史"""
    service = InformationService()
    return await service.get_analyst_ranks(ts_code, limit)

@router.post("/analyst-ranks/sync-fetch", response_model=SyncResult)
async def sync_analyst_ranks_from_src(date: Optional[str] = Query(None, description="同步日期 YYYY-MM-DD")):
    """从数据源抓取并同步机构评级"""
    service = InformationService()
    count = await service.sync_analyst_ranks_from_akshare(report_date=date)
    return SyncResult(total=count, success=count)


# -----------------------------------------------------------------------------
# Performance Forecasts
# -----------------------------------------------------------------------------
@router.post("/forecasts/sync", response_model=SyncResult)
async def sync_forecasts(request: Request, items: List[PerformanceForecastCreate]):
    """同步业绩预告数据"""
    service = InformationService()
    try:
        count = await service.sync_forecasts([item.model_dump() for item in items])
        return SyncResult(total=len(items), success=count)
    except Exception as e:
        logger.error(f"Failed to sync forecasts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecasts/{ts_code}", response_model=List[PerformanceForecastResponse])
async def get_forecasts(ts_code: str, limit: int = 20):
    """查询业绩预告历史"""
    service = InformationService()
    return await service.get_forecasts(ts_code, limit)

@router.post("/forecasts/sync-fetch", response_model=SyncResult)
async def sync_forecasts_from_src(period: str = Query(..., description="财报期 YYYY-MM-DD")):
    """从数据源抓取并同步业绩预告"""
    service = InformationService()
    count = await service.sync_forecasts_from_akshare(period=period)
    return SyncResult(total=count, success=count)


# -----------------------------------------------------------------------------
# Sentiment
# -----------------------------------------------------------------------------
@router.post("/sentiment/sync", response_model=SyncResult)
async def sync_sentiment(request: Request, items: List[SentimentDailyCreate]):
    """同步市场热度数据"""
    service = InformationService()
    try:
        count = await service.sync_sentiment([item.model_dump() for item in items])
        return SyncResult(total=len(items), success=count)
    except Exception as e:
        logger.error(f"Failed to sync sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment/{ts_code}", response_model=List[SentimentDailyResponse])
async def get_sentiment(ts_code: str, limit: int = 30):
    """查询市场热度历史"""
    service = InformationService()
    return await service.get_sentiment(ts_code, limit)

@router.post("/sentiment/sync-fetch/{ts_code}", response_model=SyncResult)
async def sync_sentiment_from_src(ts_code: str):
    """从数据源抓取并同步个股热度"""
    service = InformationService()
    count = await service.sync_sentiment_from_akshare(ts_code=ts_code)
    return SyncResult(total=1, success=count)

