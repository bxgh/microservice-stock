from fastapi import APIRouter, HTTPException, Query
from app.services.stock_info_service import stock_info_service
from typing import Dict, Any

router = APIRouter()

def normalize_code(code: str) -> str:
    """标准化代码为 600519.SH 格式"""
    code = code.upper()
    if "." in code:
        parts = code.split(".")
        if parts[0].isalpha(): # SH.600519 -> 600519.SH
            return f"{parts[1]}.{parts[0]}"
        return code # 600519.SH
    
    if code.startswith(('6', '9')):
        return f"{code}.SH"
    elif code.startswith(('4', '8', '0', '3')):
        if code.startswith(('0', '3')):
            return f"{code}.SZ"
        return f"{code}.BJ"
    return code

@router.get("/{code}/fundamentals")
async def get_stock_fundamentals(code: str):
    """个股基本面: 机构评级、业绩预告"""
    norm_code = normalize_code(code)
    data = await stock_info_service.get_fundamentals(norm_code)
    return {"code": norm_code, "data": data}

@router.get("/{code}/financials")
async def get_stock_financials(code: str, limit: int = Query(4, ge=1, le=20)):
    """个股财务: 利润简表、核心指标"""
    norm_code = normalize_code(code)
    data = await stock_info_service.get_financials(norm_code, limit)
    return {"code": norm_code, "data": data}

@router.get("/{code}/shareholders")
async def get_stock_shareholders(code: str):
    """个股股东: 股东户数、前十大股东"""
    norm_code = normalize_code(code)
    data = await stock_info_service.get_shareholders(norm_code)
    return {"code": norm_code, "data": data}

@router.get("/{code}/funds")
async def get_stock_funds(code: str):
    """个股资金: 北向持股、龙虎榜"""
    norm_code = normalize_code(code)
    data = await stock_info_service.get_funds(norm_code)
    return {"code": norm_code, "data": data}

@router.get("/{code}/dividends")
async def get_stock_dividends(code: str):
    """个股分红: (数据暂缺)"""
    norm_code = normalize_code(code)
    return {
        "code": norm_code, 
        "data": [], 
        "status": "data_insufficient",
        "message": "分红配股数据暂未入库"
    }

@router.get("/search")
async def search_stocks(keyword: str = Query(..., min_length=1)):
    """搜索股票: 支持代码、名称、拼音"""
    return await stock_info_service.search_stocks(keyword)
