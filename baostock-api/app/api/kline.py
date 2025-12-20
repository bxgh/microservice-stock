"""K线数据端点"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

import baostock as bs

router = APIRouter()
logger = logging.getLogger("baostock-api")


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
    
    try:
        # 补全股票代码前缀
        if not code.startswith(("sh.", "sz.")):
            if code.startswith("6"):
                code = f"sh.{code}"
            else:
                code = f"sz.{code}"
        
        # 复权类型映射
        adjust_map = {1: "1", 2: "2", 3: "3"}
        adjust_flag = adjust_map.get(adjust, "2")
        
        # 查询字段
        fields = "date,open,high,low,close,volume,amount,turn,pctChg"
        
        # 查询K线数据
        rs = bs.query_history_k_data_plus(
            code=code,
            fields=fields,
            start_date=start_date or "2020-01-01",
            end_date=end_date or "",
            frequency=frequency,
            adjustflag=adjust_flag,
        )
        
        if rs.error_code != "0":
            logger.error(f"BaoStock查询失败: {rs.error_msg}", extra={"request_id": request_id})
            raise HTTPException(status_code=500, detail=f"查询失败: {rs.error_msg}")
        
        result = []
        while rs.next():
            row = rs.get_row_data()
            result.append({
                "date": row[0],
                "open": float(row[1]) if row[1] else None,
                "high": float(row[2]) if row[2] else None,
                "low": float(row[3]) if row[3] else None,
                "close": float(row[4]) if row[4] else None,
                "volume": int(float(row[5])) if row[5] else None,
                "amount": float(row[6]) if row[6] else None,
                "turn": float(row[7]) if row[7] else None,
                "pctChg": float(row[8]) if row[8] else None,
            })
        
        # 限制返回数量
        result = result[-500:] if len(result) > 500 else result
        
        logger.info(f"获取K线成功: code={code}, count={len(result)}", extra={"request_id": request_id})
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取K线失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取K线失败: {str(e)}")
