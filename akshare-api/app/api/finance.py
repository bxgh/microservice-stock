"""财务数据相关端点"""
import logging
from typing import Optional
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request

import akshare as ak

router = APIRouter()
logger = logging.getLogger("akshare-api")


@router.get("/finance/{code}")
async def get_finance(request: Request, code: str):
    """
    获取股票财务报表数据
    
    - **code**: 股票代码,如 600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        # 使用akshare获取财务数据
        df = ak.stock_financial_abstract_ths(symbol=code)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="未找到财务数据")
        
        # 取最新一期数据
        latest = df.iloc[0]
        
        result = {
            "code": code,
            "total_revenue": float(latest.get("营业总收入", 0)) if latest.get("营业总收入") else None,
            "net_profit": float(latest.get("净利润", 0)) if latest.get("净利润") else None,
            "roe": float(latest.get("净资产收益率", 0)) / 100 if latest.get("净资产收益率") else None,
            "report_date": str(latest.get("报告期", "")) if latest.get("报告期") else None,
        }
        
        logger.info(f"获取财务数据成功: code={code}", extra={"request_id": request_id})
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取财务数据失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取财务数据失败: {str(e)}")


@router.get("/valuation/{code}")
async def get_valuation(request: Request, code: str):
    """
    获取股票估值指标
    
    - **code**: 股票代码,如 600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        # 获取实时行情(包含估值)
        df = ak.stock_zh_a_spot_em()
        
        # 匹配股票代码
        stock = df[df["代码"] == code]
        
        if stock.empty:
            raise HTTPException(status_code=404, detail=f"未找到股票: {code}")
        
        row = stock.iloc[0]
        
        result = {
            "code": code,
            "name": row.get("名称", ""),
            "pe": float(row.get("市盈率-动态", 0)) if row.get("市盈率-动态") else None,
            "pb": float(row.get("市净率", 0)) if row.get("市净率") else None,
            "ps": None,  # akshare实时行情不含PS
            "market_cap": float(row.get("总市值", 0)) if row.get("总市值") else None,
            "price": float(row.get("最新价", 0)) if row.get("最新价") else None,
        }
        
        logger.info(f"获取估值数据成功: code={code}", extra={"request_id": request_id})
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取估值数据失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取估值数据失败: {str(e)}")


@router.get("/valuation/{code}/history")
async def get_valuation_history(
    request: Request,
    code: str,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
):
    """
    获取股票历史估值数据
    
    - **code**: 股票代码,如 600519
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        # 使用akshare获取历史估值
        df = ak.stock_a_lg_indicator(symbol=code)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="未找到历史估值数据")
        
        # 日期过滤
        if start_date:
            df = df[df["trade_date"] >= start_date]
        if end_date:
            df = df[df["trade_date"] <= end_date]
        
        # 限制返回数量
        df = df.head(100)
        
        result = []
        for _, row in df.iterrows():
            result.append({
                "date": str(row.get("trade_date", "")),
                "pe": float(row.get("pe", 0)) if row.get("pe") else None,
                "pe_ttm": float(row.get("pe_ttm", 0)) if row.get("pe_ttm") else None,
                "pb": float(row.get("pb", 0)) if row.get("pb") else None,
                "ps": float(row.get("ps", 0)) if row.get("ps") else None,
                "ps_ttm": float(row.get("ps_ttm", 0)) if row.get("ps_ttm") else None,
                "total_mv": float(row.get("total_mv", 0)) if row.get("total_mv") else None,
            })
        
        logger.info(f"获取历史估值成功: code={code}, count={len(result)}", extra={"request_id": request_id})
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取历史估值失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取历史估值失败: {str(e)}")
