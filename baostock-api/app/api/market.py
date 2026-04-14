from fastapi import APIRouter, HTTPException, Query, Request
from app.utils.logger import get_logger
import pandas as pd

router = APIRouter()
logger = get_logger("baostock-api.market")

@router.get("/market/stocks")
async def get_market_stocks(
    request: Request,
    date: str = Query(..., description="日期 YYYY-MM-DD"),
):
    """
    获取指定日期的全市场股票列表及状态
    包括: code, tradeStatus(1正常, 0停牌), code_name
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.baostock_service
    

    try:
        # 调用 BaoStockService 封装的查询方法
        result = await service.get_all_stocks_status(date)
        
        logger.info(f"获取全市场股票状态成功: date={date}, count={len(result)}", extra={"request_id": request_id})
        return result
        
    except Exception as e:
        logger.error(f"获取全市场股票状态失败: date={date}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))
