import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
import logging

logger = logging.getLogger("gateway.auth")

security = HTTPBearer()

def create_access_token(user_id: int) -> str:
    """创建 JWT 访问令牌"""
    expire = datetime.utcnow() + timedelta(days=settings.JWT_EXPIRATION_DAYS)
    payload = {
        "uid": user_id,
        "exp": expire
    }
    encoded_jwt = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """验证 JWT 并返回 payload"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Security(security)) -> int:
    """FastAPI 依赖，用于获取当前登录用户的 ID"""
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("uid")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return user_id
