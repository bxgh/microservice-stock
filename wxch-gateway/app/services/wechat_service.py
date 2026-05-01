import httpx
import logging
import time
import os
from typing import Optional, Dict, Any
from app.utils.database import db

logger = logging.getLogger("gateway.wechat")

class WechatService:
    """微信公众号服务类 (最终稳定版 - 兼顾 API 尝试与报错容忍)"""

    def __init__(self):
        self.base_url = "https://api.weixin.qq.com"

    async def get_access_token(self, account_id: int) -> Optional[str]:
        """从数据库获取 AccessToken"""
        query = "SELECT mp_appid, access_token_encrypted, access_token_expires_at FROM mp_account WHERE id = %s"
        res = await db.execute(query, (account_id,))
        if not res: return None
        return res[0]['access_token_encrypted']

    async def upload_image(self, account_id: int, image_path: str) -> Optional[str]:
        """上传封面图 (带 SSL 忽略)"""
        token = await self.get_access_token(account_id)
        if not token: return None
        
        url = f"{self.base_url}/cgi-bin/media/upload?access_token={token}&type=image"
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            with open(image_path, "rb") as f:
                resp = await client.post(url, files={"media": ("cover.jpg", f, "image/jpeg")})
                data = resp.json()
                return data.get("media_id")

    async def add_draft(self, account_id: int, title: str, content_html: str, 
                        author: str = "八仙过海", digest: str = "", thumb_media_id: str = "") -> Optional[str]:
        """新建草稿 (带错误追踪)"""
        token = await self.get_access_token(account_id)
        if not token: return None

        if not thumb_media_id:
            from PIL import Image, ImageDraw
            cover_path = "temp_cover.jpg"
            img = Image.new('RGB', (900, 383), color=(40, 44, 52))
            ImageDraw.Draw(img).rectangle([10, 10, 890, 373], outline=(212, 167, 106), width=3)
            img.save(cover_path)
            thumb_media_id = await self.upload_image(account_id, cover_path)
            if not thumb_media_id: return None
            
        url = f"{self.base_url}/cgi-bin/draft/add?access_token={token}"
        payload = {
            "articles": [{
                "title": title, "author": author if author else "八仙过海",
                "digest": digest, "content": content_html,
                "thumb_media_id": thumb_media_id, "need_open_comment": 0
            }]
        }
        
        async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            if "media_id" in data:
                return data["media_id"]
            logger.warning(f"Draft sync officially failed: {data}")
            return None

wechat_service = WechatService()
