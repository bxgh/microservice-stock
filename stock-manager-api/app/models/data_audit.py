from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class DataAuditSummary(BaseModel):
    id: int
    data_type: str
    target: str
    trade_date: date
    level: str
    issue_count: Optional[int] = 0
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class DataAuditDetail(BaseModel):
    id: int
    summary_id: int
    dimension: str
    level: str
    message: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

class DataAuditResponse(BaseModel):
    items: List[DataAuditSummary]
    total: int
    page: int
    size: int

class DataAuditDetailResponse(BaseModel):
    items: List[DataAuditDetail]
