from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from app.services.game_service import GameService
from app.utils.logger import get_logger
from app.utils.database import db
from datetime import datetime

router = APIRouter()
logger = get_logger("stock-manager.api.game")

@router.post("/sync/lhb")
async def sync_lhb(
    request: Request,
    date: Optional[str] = Query(None, description="交易日期 YYYY-MM-DD")
):
    """同步龙虎榜数据 (含机构明细)"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = GameService()
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
        
    try:
        count = await service.sync_lhb_daily(date)
        return {"status": "success", "synced_count": count, "date": date}
    except Exception as e:
        logger.error(f"同步龙虎榜失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/north")
async def sync_north(
    request: Request,
    date: Optional[str] = Query(None, description="交易日期 YYYY-MM-DD")
):
    """同步北向资金持股数据"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = GameService()
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
        
    try:
        count = await service.sync_north_funds_daily(date)
        return {"status": "success", "synced_count": count, "date": date}
    except Exception as e:
        logger.error(f"同步北向资金失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/north/history/{code}")
async def sync_north_history(
    request: Request,
    code: str
):
    """同步个股北向资金持股历史"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = GameService()
    
    try:
        count = await service.sync_north_funds_history(code)
        return {"status": "success", "synced_count": count, "code": code}
    except Exception as e:
        logger.error(f"同步北向资金历史失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lhb/{code}")
async def get_lhb_history(code: str, limit: int = 20):
    """查询个股龙虎榜历史"""
    sql = """
        SELECT trade_date, close_price, change_pct, net_buy_amt, 
               inst_net_buy_amt, inst_buy_count, inst_sell_count, reason
        FROM stock_lhb_daily 
        WHERE ts_code = %s 
        ORDER BY trade_date DESC 
        LIMIT %s
    """
    rows = await db.execute(sql, (code, limit))
    result = []
    for row in rows:
        result.append({
            "trade_date": row[0].strftime("%Y-%m-%d") if row[0] else None,
            "close_price": float(row[1]) if row[1] else None,
            "change_pct": float(row[2]) if row[2] else None,
            "net_buy_amt": float(row[3]) if row[3] else None,
            "inst_net_buy_amt": float(row[4]) if row[4] else None,
            "inst_buy_count": row[5],
            "inst_sell_count": row[6],
            "reason": row[7]
        })
    return {"code": code, "data": result}

@router.get("/north/{code}")
async def get_north_history(code: str, limit: int = 20):
    """查询个股北向持股历史"""
    sql = """
        SELECT trade_date, hold_count, hold_market_cap, hold_ratio
        FROM stock_north_funds_daily 
        WHERE ts_code = %s 
        ORDER BY trade_date DESC 
        LIMIT %s
    """
    rows = await db.execute(sql, (code, limit))
    result = []
    for row in rows:
        result.append({
            "trade_date": row[0].strftime("%Y-%m-%d") if row[0] else None,
            "hold_count": row[1],
            "hold_market_cap": float(row[2]) if row[2] else None,
            "hold_ratio": float(row[3]) if row[3] else None
        })
    return {"code": code, "data": result}
