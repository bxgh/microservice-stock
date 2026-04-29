import json
import logging
from typing import Dict, Any
from fastapi import HTTPException
from app.utils.database import db
from app.models.user import UserProfileUpdate

logger = logging.getLogger("gateway.service.user")

class UserService:
    async def get_profile(self, user_id: int) -> Dict[str, Any]:
        query = """
            SELECT id, nickname, avatar_url, gender, region, level, expired_at,
                   quota_diary, quota_storage_mb, quota_watchlist,
                   quota_mp_account, prefs, diary_count, storage_used_kb,
                   created_at
            FROM sys_user
            WHERE id = %s AND status != 0
        """
        res = await db.execute(query, (user_id,))
        if not res:
            raise HTTPException(status_code=404, detail="User not found")

        user = res[0]
        if user.get("prefs") and isinstance(user["prefs"], str):
            try:
                user["prefs"] = json.loads(user["prefs"])
            except (json.JSONDecodeError, TypeError):
                user["prefs"] = None

        return user

    async def update_profile(self, user_id: int, data: UserProfileUpdate) -> Dict[str, Any]:
        update_fields = []
        params = []

        if data.nickname is not None:
            update_fields.append("nickname = %s")
            params.append(data.nickname)
        if data.avatar_url is not None:
            update_fields.append("avatar_url = %s")
            params.append(data.avatar_url)
        if data.gender is not None:
            update_fields.append("gender = %s")
            params.append(data.gender)
        if data.region is not None:
            update_fields.append("region = %s")
            params.append(data.region)
        if data.prefs is not None:
            update_fields.append("prefs = %s")
            params.append(json.dumps(data.prefs))

        if update_fields:
            update_fields.append("updated_at = NOW()")
            fields_str = ", ".join(update_fields)
            update_query = f"UPDATE sys_user SET {fields_str} WHERE id = %s"
            params.append(user_id)
            await db.execute(update_query, tuple(params))

        return await self.get_profile(user_id)

user_service = UserService()
