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


@router.get("/finance/historical/{code}")
async def get_historical_finance(request: Request, code: str):
    """
    获取历史全量财务报表 (盈利锚核心数据)
    
    返回包含资产负债表、利润表、现金流量表列表。
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        data = await service.get_historical_financial_report(code)
        
        if not data:
            raise HTTPException(status_code=404, detail="未找到历史财务数据")
        
        data["code"] = code
        logger.info(f"获取历史财务数据成功: code={code}", extra={"request_id": request_id})
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取历史财务数据失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取历史财务数据失败: {str(e)}")


@router.get("/finance/analysis-indicators/{code}")
async def get_analysis_indicators(request: Request, code: str):
    """
    获取财务分析指标 (ROE, ROA, 毛利率, EPS等)
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        data = await service.get_financial_analysis_indicators(code)
        if not data:
            raise HTTPException(status_code=404, detail="未找到财务分析指标数据")
        
        return {
            "code": code,
            "indicators": data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取财务分析指标失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取财务分析指标失败: {str(e)}")


@router.get("/shareholder/{code}")
async def get_shareholder(request: Request, code: str, all: bool = Query(False, description="是否获取所有历史数据")):
    """
    获取股东信息 (户数 + 前十大)
    
    - **code**: 股票代码,如 600519
    - **all**: 如果为 true, 将返回上市以来的所有股东户数及前十大股东记录
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        data = await service.get_shareholder_info(code, all_history=all)
        
        # Check if data empty? service returns dict with list inside.
        if not data:
            # Even if empty dict, return it?
             pass 
        
        logger.info(f"获取股东信息成功: code={code}, all={all}", extra={"request_id": request_id})
        return data
        
    except Exception as e:
        logger.error(f"获取股东信息失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取股东信息失败: {str(e)}")


@router.get("/dividend/{code}")
async def get_dividend(request: Request, code: str):
    """
    获取分红配股历史
    
    - **code**: 股票代码,如 600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        data = await service.get_dividend_history(code)
        logger.info(f"获取分红配股信息成功: code={code}, count={len(data)}", extra={"request_id": request_id})
        return data
        
    except Exception as e:
        logger.error(f"获取分红配股信息失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取分红配股信息失败: {str(e)}")


@router.get("/forecast")
async def get_forecast_data(request: Request, period: str = Query(..., description="报告期 YYYY-MM-DD")):
    """
    获取业绩预告
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        data = await service.get_performance_forecast(period)
        # 允许返回空列表
        if data is None: 
            data = []
        logger.info(f"获取业绩预告成功: period={period}, count={len(data)}", extra={"request_id": request_id})
        return data
    except Exception as e:
        logger.error(f"获取业绩预告失败: period={period}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))
