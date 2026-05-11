"""
同步状态数据模型
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class SyncStatus(str, Enum):
    """同步状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class SyncRecord(BaseModel):
    """同步任务记录"""
    task_id: str = Field(..., description="任务ID")
    status: SyncStatus = Field(..., description="同步状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    total_count: int = Field(0, description="总记录数")
    success_count: int = Field(0, description="成功记录数")
    failed_count: int = Field(0, description="失败记录数")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    model_config = {
        "from_attributes": True
    }
