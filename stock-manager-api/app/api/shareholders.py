"""股东数据相关 API"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.shareholder_service import ShareholderService
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("stock-manager.api.shareholders")


class BatchSyncRequest(BaseModel):
    """批量同步请求"""
    codes: List[str]


@router.post("/sync/{code}")
async def sync_shareholder_data(
    request: Request,
    code: str,
    all: bool = Query(False, description="是否获取全量历史数据")
):
    """
    同步单只股票的股东数据
    
    - **code**: 股票代码，如 600519
    - **all**: 是否获取全量历史数据，默认 false (仅获取近期数据)
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = ShareholderService()
    
    try:
        result = await service.sync_single_stock(code, all_history=all)
        logger.info(f"同步股东数据成功: code={code}, all={all}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"同步股东数据失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/sync-batch")
async def sync_batch_shareholder_data(
    request: Request,
    body: BatchSyncRequest,
    all: bool = Query(False, description="是否获取全量历史数据")
):
    """
    批量同步股东数据
    
    - **codes**: 股票代码列表
    - **all**: 是否获取全量历史数据
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = ShareholderService()
    
    try:
        result = await service.sync_batch(body.codes, all_history=all)
        logger.info(
            f"批量同步股东数据完成: total={result['total']}, success={result['success']}, failed={result['failed']}",
            extra={"request_id": request_id}
        )
        return result
    except Exception as e:
        logger.error(f"批量同步股东数据失败: error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"批量同步失败: {str(e)}")


@router.get("/count/{code}")
async def get_holder_count(
    request: Request,
    code: str,
    limit: int = Query(100, description="返回记录数", le=1000)
):
    """
    查询股东户数历史
    
    - **code**: 股票代码
    - **limit**: 返回记录数，最多 1000 条
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = ShareholderService()
    
    try:
        results = await service.get_holder_count_history(code, limit)
        logger.info(f"查询股东户数成功: code={code}, count={len(results)}", extra={"request_id": request_id})
        return {"code": code, "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"查询股东户数失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/top10/{code}")
async def get_top10_holders(
    request: Request,
    code: str,
    date: Optional[str] = Query(None, description="截止日期，如 2025-09-30，不指定则返回最新")
):
    """
    查询前十大股东
    
    - **code**: 股票代码
    - **date**: 截止日期，不指定则返回最新一期
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = ShareholderService()
    
    try:
        results = await service.get_top10_holders(code, end_date=date)
        logger.info(f"查询前十大股东成功: code={code}, count={len(results)}", extra={"request_id": request_id})
        return {"code": code, "date": date, "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"查询前十大股东失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
