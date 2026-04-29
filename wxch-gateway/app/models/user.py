from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class UserProfile(BaseModel):
    id: int
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: int
    region: Optional[str] = None
    level: int
    expired_at: Optional[datetime] = None
    quota_diary: Optional[int] = None
    quota_storage_mb: Optional[int] = None
    quota_watchlist: Optional[int] = None
    quota_mp_account: Optional[int] = None
    prefs: Optional[Dict[str, Any]] = None
    diary_count: int
    storage_used_kb: int
    created_at: datetime

class UserProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: Optional[int] = None
    region: Optional[str] = None
    prefs: Optional[Dict[str, Any]] = None
