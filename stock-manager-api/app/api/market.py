from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from app.utils.database import db
from app.utils.logger import get_logger
from app.utils.code_utils import normalize_ts_code

router = APIRouter()
logger = get_logger("stock-manager.market")

@router.get("/kline")
async def get_kline(
    ts_code: str = Query(..., description="股票代码, 如 600519.SH"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(200, description="返回条数", ge=1, le=5000)
):
    """获取日线行情 (前复权)
    
    使用 v_stock_kline_forward_adj 视图，返回字段已将 adj_close 等映射为标准 close。
    """
    try:
        ts_code = normalize_ts_code(ts_code)
        
        # 基础 SQL
        # 我们将 adj_xxx 映射为 xxx，让前端无感知切换
        sql = """
            SELECT 
                trade_date,
                adj_open as open,
                adj_high as high,
                adj_low as low,
                adj_close as close,
                adj_pre_close as pre_close,
                pct_chg,
                volume,
                amount,
                adjust_factor
            FROM v_stock_kline_forward_adj
            WHERE ts_code = %s
        """
        params = [ts_code]
        
        if start_date:
            sql += " AND trade_date >= %s"
            params.append(start_date)
        if end_date:
            sql += " AND trade_date <= %s"
            params.append(end_date)
            
        sql += " ORDER BY trade_date DESC LIMIT %s"
        params.append(limit)
        
        rows = await db.execute(sql, tuple(params))
        
        results = []
        for r in rows:
            results.append({
                "trade_date": str(r[0]),
                "open": float(r[1]) if r[1] is not None else 0,
                "high": float(r[2]) if r[2] is not None else 0,
                "low": float(r[3]) if r[3] is not None else 0,
                "close": float(r[4]) if r[4] is not None else 0,
                "pre_close": float(r[5]) if r[5] is not None else 0,
                "pct_chg": float(r[6]) if r[6] is not None else 0,
                "volume": float(r[7]) if r[7] is not None else 0,
                "amount": float(r[8]) if r[8] is not None else 0,
                "adj_factor": float(r[9]) if r[9] is not None else 1.0
            })
            
        return {"ts_code": ts_code, "data": results}
        
    except Exception as e:
        logger.error(f"获取 K 线失败: {ts_code}, {e}")
        raise HTTPException(status_code=500, detail=str(e))
