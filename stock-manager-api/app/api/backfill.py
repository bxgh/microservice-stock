from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from app.utils.database import db
from app.utils.logger import get_logger
from pydantic import BaseModel
from datetime import date

router = APIRouter()
logger = get_logger("stock-manager.api.backfill")


class SignalAck(BaseModel):
    request_id: str
    status: str = "COMPLETED"
    notes: str = None


@router.get("/recalc-signals/pending")
async def get_pending_signals(limit: int = Query(50, ge=1, le=200)):
    """获取待重算的信号列表 (供内网节点调用)"""
    try:
        sql = """
            SELECT id, ts_code, start_date, end_date, request_id, created_at
            FROM recalc_signal
            WHERE status = 'PENDING'
            ORDER BY created_at ASC
            LIMIT %s
        """
        rows = await db.execute(sql, (limit,))

        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "ts_code": row[1],
                "start_date": row[2].isoformat() if isinstance(row[2], (date,)) else row[2],
                "end_date": row[3].isoformat() if isinstance(row[3], (date,)) else row[3],
                "request_id": row[4],
                "created_at": row[5].isoformat() if row[5] else None
            })

            # 自动将拉取到的信号标记为 PROCESSING
            await db.execute(
                "UPDATE recalc_signal SET status='PROCESSING' WHERE id=%s",
                (row[0],)
            )

        return {"count": len(results), "data": results}
    except Exception as e:
        logger.error(f"获取重算信号失败: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/recalc-signals/ack")
async def acknowledge_signal(ack: SignalAck):
    """确认重算完成"""
    try:
        # 根据 request_id 更新状态
        sql = """
            UPDATE recalc_signal
            SET status = %s, updated_at = NOW()
            WHERE request_id = %s
        """
        await db.execute(sql, (ack.status, ack.request_id))

        logger.info(f"信号已确认完成: {ack.request_id} | Status: {ack.status}")
        return {"status": "success", "request_id": ack.request_id}
    except Exception as e:
        logger.error(f"确认信号失败: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
