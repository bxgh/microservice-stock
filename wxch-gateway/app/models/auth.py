from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class LoginRequest(BaseModel):
    code: str = Field(..., description="微信 wx.login 获取的临时登录凭证")

class UserInfo(BaseModel):
    id: int
    nickname: str
    level: int
    prefs: Optional[Dict[str, Any]] = None

class LoginData(BaseModel):
    token: str
    user_info: UserInfo

class LoginResponse(BaseModel):
    code: int = 200
    data: LoginData
    message: str = "登录成功"
