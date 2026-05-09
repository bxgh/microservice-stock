from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DQFindingBase(BaseModel):
    ts_code: str
    trade_date: date
    check_type: str = Field(
        ...,
        description="CROSS_SOURCE, INTEGRITY, CONTINUITY, BUSINESS_RULE, FACTOR_RECONCILE")
    severity: str = "WARN"
    finding_msg: str
    diff_data: Optional[Dict[str, Any]] = None
    status: int = 0
    is_deleted: bool = False


class DQFindingCreate(DQFindingBase):
    pass


class DQFinding(DQFindingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DQReportSummary(BaseModel):
    check_date: date
    total_scanned: int
    total_issues: int
    severity_dist: Dict[str, int]
    check_type_dist: Dict[str, int]


class DQMetricItem(BaseModel):
    indicator_name: str
    indicator_value: float
    target_value: float
    status: str


class DQMetricsReport(BaseModel):
    trade_date: date
    metrics: List[DQMetricItem]
