"""估值数据端点"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("baostock-api.api.valuation")


@router.get("/valuation/{code}/history")
async def get_valuation_history(
    request: Request,
    code: str,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
):
    """
    获取历史估值数据 (PE/PB)
    
    - **code**: 股票代码,如 sh.600519 或 sz.000001
    - **start_date**: 开始日期，默认 2020-01-01
    - **end_date**: 结束日期，默认至今
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.baostock_service
    
    try:
        result = await service.get_valuation_history(
            code=code,
            start_date=start_date or "2020-01-01",
            end_date=end_date or ""
        )
        
        if not result:
            logger.warning(f"未获取到估值数据: code={code}", extra={"request_id": request_id})
            return []
            
        logger.info(f"获取历史估值成功: code={code}, count={len(result)}", extra={"request_id": request_id})
        return result
        
    except Exception as e:
        logger.error(f"获取历史估值失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取历史估值失败: {str(e)}")
