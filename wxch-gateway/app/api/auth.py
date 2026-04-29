from fastapi import APIRouter
from app.models.auth import LoginRequest, LoginResponse
from app.services.auth_service import auth_service

router = APIRouter()

@router.post("/login", response_model=LoginResponse, summary="微信小程序无感静默登录")
async def login(request: LoginRequest):
    """
    实现微信小程序无感静默登录，建立小程序端与后端 sys_user 表的身份关联，并发放 JWT 访问凭证。
    """
    return await auth_service.login_with_wechat(request.code)
