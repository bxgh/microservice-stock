"""K线数据端点"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("baostock-api.api.kline")


@router.get("/history/kline/{code}")
async def get_history_kline(
    request: Request,
    code: str,
    frequency: str = Query("d", description="频率: d=日, w=周, m=月, 5=5分钟"),
    adjust: int = Query(2, ge=1, le=3, description="复权: 1=后复权, 2=前复权, 3=不复权"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
):
    """
    获取历史K线数据
    
    - **code**: 股票代码,如 sh.600519 或 sz.000001
    - **frequency**: d=日线, w=周线, m=月线, 5=5分钟, 15=15分钟, 30=30分钟, 60=60分钟
    - **adjust**: 1=后复权, 2=前复权, 3=不复权
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.baostock_service
    
    try:
        # 复权类型映射
        adjust_map = {1: "1", 2: "2", 3: "3"}
        adjust_flag = adjust_map.get(adjust, "2")
        
        result = await service.get_kline(
            code=code,
            frequency=frequency,
            adjust=adjust_flag,
            start_date=start_date or "2020-01-01",
            end_date=end_date or ""
        )
        
        if not result:
            logger.warning(f"未获取到K线数据: code={code}", extra={"request_id": request_id})
            return []
            
        logger.info(f"获取K线成功: code={code}, count={len(result)}", extra={"request_id": request_id})
        return result
        
    except Exception as e:
        logger.error(f"获取K线失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取K线失败: {str(e)}")
