"""指数与行业数据端点"""
from fastapi import APIRouter, HTTPException, Request
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("baostock-api.api.index")


@router.get("/index/cons/{index}")
async def get_index_constituents(request: Request, index: str):
    """
    获取指数成分股
    
    - **index**: 指数代码,如 sz.399300 (沪深300), sh.000016 (上证50)
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.baostock_service
    
    try:
        result = await service.get_index_cons(index)
        
        if not result:
            logger.warning(f"获取指数成分成功(空): index={index}", extra={"request_id": request_id})
            
        logger.info(f"获取指数成分成功: index={index}, count={len(result)}", extra={"request_id": request_id})
        return {"index": index, "constituents": result}
        
    except Exception as e:
        logger.error(f"获取指数成分失败: index={index}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取指数成分失败: {str(e)}")


@router.get("/industry/classify")
async def get_industry_classify(request: Request):
    """获取行业分类"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.baostock_service
    
    try:
        result = await service.get_industry_classify()
        logger.info(f"获取行业分类成功: count={len(result)}", extra={"request_id": request_id})
        return result
        
    except Exception as e:
        logger.error(f"获取行业分类失败: error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取行业分类失败: {str(e)}")


@router.get("/finance/profit/{code}")
async def get_profit_data(request: Request, code: str):
    """
    获取盈利能力数据
    
    - **code**: 股票代码,如 sh.600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.baostock_service
    
    try:
        # 查询 2024 Q3 (示例，实际应根据当前时间动态调整或由参数传入)
        data = await service.get_profit_data(code=code, year=2024, quarter=3)
        
        if not data:
            raise HTTPException(status_code=404, detail="未找到盈利数据")
        
        logger.info(f"获取盈利能力成功: code={code}", extra={"request_id": request_id})
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取盈利能力失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取盈利能力失败: {str(e)}")
