import uuid
from fastapi import APIRouter, HTTPException, Request
from app.models.quote import SpotResponse, SnapshotResponse, TimeShareResponse
from app.services.quote_service import quote_service
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("gateway.api.quote")


def _error_response(code: str, message: str, request_id: str) -> dict:
    """生成符合项目规范的错误响应体"""
    return {"error": {"code": code, "message": message, "request_id": request_id}}


@router.get("/{code}/spot", response_model=SpotResponse)
async def get_stock_spot(code: str, request: Request):
    """获取股票实时行情 (轻量版)

    返回最新价、涨跌幅、成交量等核心数据。
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])
    logger.info(f"获取实时行情: code={code}", extra={"request_id": request_id})

    data = await quote_service.get_spot(code)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=_error_response("QUOTE_NOT_FOUND", f"未找到股票 {code} 的实时数据", request_id)
        )
    return {"data": data}


@router.get("/{code}/snapshot", response_model=SnapshotResponse)
async def get_stock_snapshot(code: str, request: Request):
    """获取股票快照行情 (含五档盘口与估值)

    返回完整盘口 (买卖各五档)、PE/PB 估值及总市值/流通市值。
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])
    logger.info(f"获取快照行情: code={code}", extra={"request_id": request_id})

    data = await quote_service.get_snapshot(code)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=_error_response("SNAPSHOT_NOT_FOUND", f"未找到股票 {code} 的快照数据", request_id)
        )
    return {"data": data}


@router.get("/{code}/time_share", response_model=TimeShareResponse)
async def get_stock_time_share(code: str, request: Request):
    """获取个股分时数据

    返回当天的价格点阵（通常为 241 个点）。
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])
    logger.info(f"获取分时行情: code={code}", extra={"request_id": request_id})

    result = await quote_service.get_time_share(code)
    # 返回空字典表示上游取数据失败
    if not result:
        raise HTTPException(
            status_code=404,
            detail=_error_response("TIMESHARE_NOT_FOUND", f"未找到股票 {code} 的分时数据", request_id)
        )
    # 返回服务层已组装好的 dict，内部已包含 code / 统计 / data 字段
    return result
