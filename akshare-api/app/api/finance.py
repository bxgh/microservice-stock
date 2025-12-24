"""财务数据相关端点"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("akshare-api.api.finance")


@router.get("/finance/{code}")
async def get_finance(request: Request, code: str):
    """
    获取股票财务报表数据
    
    - **code**: 股票代码,如 600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        data = await service.get_financial_abstract(code)
        
        if not data:
            raise HTTPException(status_code=404, detail="未找到财务数据")
        
        data["code"] = code
        logger.info(f"获取财务数据成功: code={code}", extra={"request_id": request_id})
        return data
        
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
    service = request.app.state.akshare_service
    
    try:
        data = await service.get_valuation_spot(code)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"未找到股票: {code}")
        
        data["code"] = code
        data["ps"] = None  # akshare实时行情通常不含PS
        
        logger.info(f"获取估值数据成功: code={code}", extra={"request_id": request_id})
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取估值数据失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取估值数据失败: {str(e)}")


@router.get("/finance/indicators/{code}")
async def get_finance_indicators(request: Request, code: str):
    """
    获取全量财务指标 (EPIC-002)
    
    包含资产、负债、权益、营收及派生指标 (EBITDA, FCF等)。
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        data = await service.get_full_financial_report(code)
        
        if not data:
            raise HTTPException(status_code=404, detail="未找到财务指标数据，请检查代码或报告期")
        
        data["code"] = code
        logger.info(f"获取全量财务指标成功: code={code}", extra={"request_id": request_id})
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取财务指标失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取财务指标失败: {str(e)}")

