from fastapi import APIRouter, Request, Query, HTTPException
from typing import Optional, List, Dict, Any
from app.services.tushare_service import TushareService

router = APIRouter()

def get_service(request: Request) -> TushareService:
    return request.app.state.tushare_service

@router.get("/stock/basic")
async def stock_basic(request: Request, list_status: str = 'L'):
    service = get_service(request)
    try:
        data = await service.get_stock_basic(list_status=list_status)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stock/daily")
async def stock_daily(
    request: Request,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    service = get_service(request)
    try:
        data = await service.get_daily(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stock/adj_factor")
async def stock_adj_factor(
    request: Request,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    service = get_service(request)
    try:
        data = await service.get_adj_factor(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trade_cal")
async def trade_cal(
    request: Request,
    exchange: str = '',
    start_date: str = '',
    end_date: str = '',
    is_open: Optional[int] = Query(None)
):
    service = get_service(request)
    try:
        data = await service.get_trade_cal(exchange=exchange, start_date=start_date, end_date=end_date, is_open=is_open)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/basic")
async def index_basic(request: Request, market: str = ''):
    service = get_service(request)
    try:
        data = await service.get_index_basic(market=market)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/daily")
async def index_daily(
    request: Request,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    service = get_service(request)
    try:
        data = await service.get_index_daily(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suspend_d")
async def suspend_d(
    request: Request,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    service = get_service(request)
    try:
        data = await service.get_suspend_d(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast")
async def forecast(
    request: Request,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = None
):
    service = get_service(request)
    try:
        data = await service.get_forecast(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/express")
async def express(
    request: Request,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = None
):
    service = get_service(request)
    try:
        data = await service.get_express(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dividend")
async def dividend(
    request: Request,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    imp_ann_date: Optional[str] = None
):
    service = get_service(request)
    try:
        data = await service.get_dividend(ts_code=ts_code, ann_date=ann_date, imp_ann_date=imp_ann_date)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stk_holdernumber")
async def stk_holdernumber(
    request: Request,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    service = get_service(request)
    try:
        data = await service.get_stk_holdernumber(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top10_holders")
async def top10_holders(
    request: Request,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = None
):
    service = get_service(request)
    try:
        data = await service.get_top10_holders(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stk_rating")
async def stk_rating(
    request: Request,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    service = get_service(request)
    try:
        data = await service.get_stk_rating(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
