import httpx
import logging
import time
import os
from typing import Optional, Dict, Any
from app.utils.database import db

logger = logging.getLogger("gateway.wechat")

class WechatService:
    """微信公众号服务类，处理 AccessToken 及草稿箱同步"""

    async def get_access_token(self, account_id: int) -> Optional[str]:
        """获取有效的 AccessToken (带缓存逻辑)"""
        query = """
            SELECT mp_appid, mp_appsecret, access_token_encrypted, access_token_expires_at 
            FROM mp_account WHERE id = %s
        """
        res = await db.execute(query, (account_id,))
        if not res:
            return None
        
        row = res[0]
        now = int(time.time())
        
        if row['access_token_encrypted'] and row['access_token_expires_at']:
            expires_at = int(row['access_token_expires_at'].timestamp())
            if expires_at > now + 300:
                return row['access_token_encrypted']
        
        appid = row['mp_appid']
        secret = row.get('mp_appsecret')
        
        if not secret:
            logger.error(f"Account {account_id} has no AppSecret configured")
            return None
            
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret
        }
        
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
            
            if "access_token" in data:
                token = data["access_token"]
                expires_in = data["expires_in"]
                
                update_query = """
                    UPDATE mp_account 
                    SET access_token_encrypted = %s, access_token_expires_at = FROM_UNIXTIME(%s) 
                    WHERE id = %s
                """
                await db.execute(update_query, (token, now + expires_in, account_id))
                return token
            else:
                logger.error(f"Failed to get wechat token: {data}")
                return None

    async def upload_image(self, account_id: int, image_path: str) -> Optional[str]:
        """上传永久素材(图片) - 草稿箱必须使用永久素材"""
        token = await self.get_access_token(account_id)
        if not token:
            return None
            
        url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
        
        async with httpx.AsyncClient(verify=False) as client:
            with open(image_path, "rb") as f:
                files = {"media": ("cover.jpg", f, "image/jpeg")}
                resp = await client.post(url, files=files)
                data = resp.json()
                
                if "media_id" in data:
                    return data["media_id"]
                else:
                    logger.error(f"Failed to upload permanent image: {data}")
                    return None

    async def _create_default_cover(self) -> str:
        """生成默认封面图"""
        from PIL import Image, ImageDraw
        path = "temp_cover.jpg"
        img = Image.new('RGB', (900, 383), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.rectangle([10, 10, 890, 373], outline=(255, 255, 255), width=2)
        img.save(path)
        return path

    async def add_draft(self, account_id: int, title: str, content_html: str, 
                        author: str = "", digest: str = "", thumb_media_id: str = "") -> Optional[str]:
        """新建草稿"""
        if not thumb_media_id:
            cover_path = await self._create_default_cover()
            thumb_media_id = await self.upload_image(account_id, cover_path)
            if not thumb_media_id:
                logger.error("Failed to get thumb_media_id, cannot add draft")
                return None
            
        token = await self.get_access_token(account_id)
        if not token:
            return None
            
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
        
        payload = {
            "articles": [
                {
                    "title": title,
                    "author": author,
                    "digest": digest,
                    "content": content_html,
                    "thumb_media_id": thumb_media_id,
                    "need_open_comment": 0
                }
            ]
        }
        
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            
            if "media_id" in data:
                return data["media_id"]
            else:
                logger.error(f"Failed to add draft: {data}")
                return None

wechat_service = WechatService()
