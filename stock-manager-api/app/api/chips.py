from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from app.services.chip_service import ChipService
from app.utils.database import db
from app.utils.logger import get_logger
from datetime import datetime, timedelta

router = APIRouter()
logger = get_logger("stock-manager.api.chips")


@router.post("/sync/restricted")
async def sync_restricted_release(
    request: Request,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD")
):
    """同步限售解禁数据"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = ChipService()

    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if not end_date:
        # Default look ahead 60 days to get upcoming pressure
        end_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

    try:
        count = await service.sync_restricted_release(start_date, end_date)
        return {
            "status": "success",
            "synced_count": count,
            "start_date": start_date,
            "end_date": end_date}
    except Exception as e:
        logger.error(f"同步限售解禁失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/block_trade")
async def sync_block_trade(
    request: Request,
    date: Optional[str] = Query(None, description="交易日期 YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD")
):
    """同步大宗交易数据 (支持单日或范围)"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = ChipService()

    try:
        if start_date and end_date:
            count = await service.sync_block_trade_range(start_date, end_date)
            return {
                "status": "success",
                "synced_count": count,
                "start_date": start_date,
                "end_date": end_date}
        else:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            count = await service.sync_block_trade(date)
            return {"status": "success", "synced_count": count, "date": date}
    except Exception as e:
        logger.error(f"同步大宗交易失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/restricted/{code}")
async def get_restricted_release(code: str):
    """查询个股限售解禁计划"""
    sql = "SELECT release_date, release_count, release_market_cap, ratio, holder_type FROM stock_restricted_release WHERE ts_code = %s ORDER BY release_date ASC"
    rows = await db.execute(sql, (code,))
    result = []
    for row in rows:
        result.append({
            "release_date": row[0].strftime("%Y-%m-%d") if row[0] else None,
            "release_count": row[1],
            "release_market_cap": float(row[2]) if row[2] else None,
            "ratio": float(row[3]) if row[3] else None,
            "holder_type": row[4]
        })
    return {"code": code, "data": result}


@router.get("/block_trade/{code}")
async def get_block_trade(code: str, limit: int = 20):
    """查询个股大宗交易记录"""
    sql = "SELECT trade_date, price, volume, amount, buyer, seller FROM stock_block_trade WHERE ts_code = %s ORDER BY trade_date DESC LIMIT %s"
    rows = await db.execute(sql, (code, limit))
    result = []
    for row in rows:
        result.append({
            "trade_date": row[0].strftime("%Y-%m-%d") if row[0] else None,
            "price": float(row[1]) if row[1] else None,
            "volume": row[2],
            "amount": float(row[3]) if row[3] else None,
            "buyer": row[4],
            "seller": row[5]
        })
    return {"code": code, "data": result}
