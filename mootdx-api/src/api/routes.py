"""
Mootdx API Routes
API 路由定义
"""
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Depends

from handlers.mootdx_handler import MootdxHandler

router = APIRouter()


def get_handler() -> MootdxHandler:
    """依赖注入：获取 Handler"""
    from main import get_handler as _get_handler
    handler = _get_handler()
    if not handler:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return handler


@router.get("/quotes")
async def get_quotes(
    codes: str = Query(..., description="股票代码，逗号分隔"),
    handler: MootdxHandler = Depends(get_handler)
):
    """
    获取实时行情
    
    - **codes**: 股票代码列表，逗号分隔 (如 "600519,000001")
    """
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        raise HTTPException(status_code=400, detail="codes is required")
    
    df = await handler.get_quotes(code_list, {})
    return df.to_dict(orient="records")


@router.get("/tick/{code}")
async def get_tick(
    code: str,
    date: Optional[int] = Query(None, description="交易日期 YYYYMMDD（整数）"),
    start: int = Query(0, description="起始位置"),
    offset: int = Query(800, ge=1, le=10000, description="获取数量"),
    handler: MootdxHandler = Depends(get_handler)
):
    """
    获取分笔成交数据
    
    - **code**: 股票代码
    - **date**: 交易日期（整数格式 YYYYMMDD，如 20260106）
    - **start**: 起始位置（默认 0）
    - **offset**: 获取数量（默认 800）
    
    返回字段 (已标准化):
    - **time**: 时间 (HH:MM)
    - **price**: 成交价
    - **volume**: 成交量 (单位：股)
    - **type**: 买卖类型 (BUY/SELL/NEUTRAL)
    """
    params = {}
    if date is not None:
        params["date"] = date
    if start is not None:
        params["start"] = start
    if offset is not None:
        params["offset"] = offset
    
    df = await handler.get_tick([code], params)
    return df.to_dict(orient="records")


@router.get("/history/{code}")
async def get_history(
    code: str,
    frequency: str = Query("d", description="频率: d=日线, w=周线, m=月线"),
    offset: int = Query(500, ge=1, le=800, description="数据条数"),
    handler: MootdxHandler = Depends(get_handler)
):
    """
    获取历史K线数据
    
    - **code**: 股票代码
    - **frequency**: d=日线, w=周线, m=月线
    - **offset**: 数据条数 (最大800)
    """
    params = {"frequency": frequency, "offset": offset}
    df = await handler.get_history([code], params)
    return df.to_dict(orient="records")


@router.get("/stocks")
async def get_stocks(
    market: Optional[int] = Query(None, description="市场: 0=深圳, 1=上海, 空=全市场"),
    handler: MootdxHandler = Depends(get_handler)
):
    """
    获取股票列表
    
    - **market**: 0=深圳, 1=上海, 不传=全市场
    """
    params = {"market": market} if market is not None else {}
    df = await handler.get_stocks([], params)
    return df.to_dict(orient="records")


@router.get("/finance/{code}")
async def get_finance(
    code: str,
    handler: MootdxHandler = Depends(get_handler)
):
    """
    获取财务基础信息
    
    - **code**: 股票代码
    """
    df = await handler.get_finance_info([code], {})
    return df.to_dict(orient="records")


@router.get("/xdxr/{code}")
async def get_xdxr(
    code: str,
    handler: MootdxHandler = Depends(get_handler)
):
    """
    获取除权除息数据
    
    - **code**: 股票代码
    """
    df = await handler.get_xdxr([code], {})
    return df.to_dict(orient="records")


@router.get("/index/bars/{code}")
async def get_index_bars(
    code: str,
    frequency: str = Query("d", description="频率: d=日线, w=周线, m=月线"),
    offset: int = Query(500, ge=1, le=800, description="数据条数"),
    handler: MootdxHandler = Depends(get_handler)
):
    """
    获取指数K线数据
    
    - **code**: 指数代码 (000001=上证, 399001=深成, 399006=创业板)
    - **frequency**: d=日线, w=周线, m=月线
    - **offset**: 数据条数 (最大800)
    """
    params = {"frequency": frequency, "offset": offset}
    df = await handler.get_index_bars([code], params)
    return df.to_dict(orient="records")
