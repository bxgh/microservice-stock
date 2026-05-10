from datetime import date, datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

class MetaRepairLogBase(BaseModel):
    finding_id: int = Field(..., description="关联的 dq_findings ID")
    ts_code: Optional[str] = None
    trade_date: Optional[date] = None
    table_name: str
    repair_type: str = "CONSENSUS"
    source_used: str
    before_snapshot: Optional[Any] = None
    after_snapshot: Optional[Any] = None
    status: str = "PENDING"
    error_msg: Optional[str] = None

class MetaRepairLogCreate(MetaRepairLogBase):
    pass

class MetaRepairLog(MetaRepairLogBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
