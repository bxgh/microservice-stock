import httpx
import json
from app.config import settings
from app.utils.database import db
from app.utils.auth import create_access_token
from app.models.auth import LoginResponse, LoginData, UserInfo
import logging
from fastapi import HTTPException

logger = logging.getLogger("gateway.service.auth")

class AuthService:
    async def login_with_wechat(self, code: str) -> LoginResponse:
        # 1. 调用微信接口获取 openid
        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": settings.WECHAT_APPID,
            "secret": settings.WECHAT_SECRET,
            "js_code": code,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                logger.error(f"WeChat API error: HTTP {response.status_code}")
                raise HTTPException(status_code=502, detail="WeChat API unavailable")
            
            data = response.json()
            if "errcode" in data and data["errcode"] != 0:
                logger.error(f"WeChat API error: {data['errcode']} - {data.get('errmsg')}")
                raise HTTPException(status_code=400, detail=f"WeChat login failed: {data.get('errmsg')}")
            
            openid = data.get("openid")
            unionid = data.get("unionid") # Optional
            
            if not openid:
                logger.error("WeChat API response missing openid")
                raise HTTPException(status_code=400, detail="Invalid WeChat response")

        # 2. 查询数据库中是否存在该 openid
        query = "SELECT id, nickname, level, prefs FROM sys_user WHERE openid = %s LIMIT 1"
        rows = await db.execute(query, (openid,))
        
        user_id = None
        nickname = None
        level = 0
        prefs = None
        
        if rows:
            # 老用户: 更新 last_login_at
            user_row = rows[0]
            user_id = user_row["id"]
            nickname = user_row["nickname"]
            level = user_row["level"]
            prefs_str = user_row.get("prefs")
            
            if prefs_str:
                try:
                    prefs = json.loads(prefs_str)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Failed to parse prefs for user {user_id}")
                    prefs = None
            
            update_query = "UPDATE sys_user SET last_login_at = NOW() WHERE id = %s"
            await db.execute(update_query, (user_id,))
            logger.info("Existing user logged in", extra={"extra_data": {"user_id": user_id}})
        else:
            # 新用户: 插入数据
            default_prefs = {
                "notification": {
                    "subscribe_morning_brief": True,
                    "subscribe_price_alert": False
                },
                "ui": {
                    "theme": "standard",
                    "senior_mode": False
                },
                "diary": {
                    "default_entry_type": 5,
                    "auto_save_interval": 60
                }
            }
            prefs_json = json.dumps(default_prefs)
            nickname = "新用户"
            level = 0
            
            insert_query = """
                INSERT INTO sys_user 
                (openid, unionid, nickname, status, level, prefs, last_login_at, created_at, updated_at) 
                VALUES (%s, %s, %s, 1, %s, %s, NOW(), NOW(), NOW())
            """
            user_id = await db.execute_insert(insert_query, (openid, unionid, nickname, level, prefs_json))
            
            prefs = default_prefs
            logger.info("New user created", extra={"extra_data": {"user_id": user_id, "openid": openid}})

        if not user_id:
            logger.error("Failed to create or retrieve user ID")
            raise HTTPException(status_code=500, detail="Failed to create or retrieve user")

        # 3. 发放 JWT Token
        token = create_access_token(user_id)
        
        user_info = UserInfo(
            id=user_id,
            nickname=nickname,
            level=level,
            prefs=prefs
        )
        
        return LoginResponse(
            data=LoginData(token=token, user_info=user_info)
        )

auth_service = AuthService()
