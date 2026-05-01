import httpx
import logging
import time
import os
from typing import Optional, Dict, Any
from app.utils.database import db

logger = logging.getLogger("gateway.wechat")

class WechatService:
    """微信公众号服务类 (白名单模式 - SSL 兼容版)"""

    def __init__(self):
        self.base_url = "https://api.weixin.qq.com"

    async def get_access_token(self, account_id: int) -> Optional[str]:
        """获取有效的 AccessToken"""
        query = "SELECT mp_appid, access_token_encrypted, access_token_expires_at FROM mp_account WHERE id = %s"
        res = await db.execute(query, (account_id,))
        if not res:
            return None
        
        account = res[0]
        token = account['access_token_encrypted']
        expires_at = account['access_token_expires_at']
        
        if token and expires_at and expires_at.timestamp() > time.time() + 300:
            return token
            
        return token

    async def upload_image(self, account_id: int, image_path: str) -> Optional[str]:
        """上传素材 (跳过 SSL 验证)"""
        token = await self.get_access_token(account_id)
        if not token:
            return None
            
        url = f"{self.base_url}/cgi-bin/media/upload?access_token={token}&type=image"
        
        # 使用 verify=False 跳过证书验证
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            with open(image_path, "rb") as f:
                files = {"media": ("cover.jpg", f, "image/jpeg")}
                resp = await client.post(url, files=files)
                data = resp.json()
                
                if "media_id" in data:
                    return data["media_id"]
                else:
                    logger.error(f"Material upload failed: {data}")
                    return None

    async def _create_default_cover(self) -> str:
        """生成默认封面图"""
        from PIL import Image, ImageDraw
        path = "temp_cover.jpg"
        img = Image.new('RGB', (900, 383), color=(40, 44, 52))
        d = ImageDraw.Draw(img)
        d.rectangle([10, 10, 890, 373], outline=(212, 167, 106), width=3)
        img.save(path)
        return path

    async def add_draft(self, account_id: int, title: str, content_html: str, 
                        author: str = "八仙过海", digest: str = "", thumb_media_id: str = "") -> Optional[str]:
        """新建草稿 (跳过 SSL 验证)"""
        token = await self.get_access_token(account_id)
        if not token:
            return None

        if not thumb_media_id:
            cover_path = await self._create_default_cover()
            thumb_media_id = await self.upload_image(account_id, cover_path)
            if not thumb_media_id:
                return None
            
        url = f"{self.base_url}/cgi-bin/draft/add?access_token={token}"
        
        payload = {
            "articles": [
                {
                    "title": title,
                    "author": author if author else "八仙过海",
                    "digest": digest,
                    "content": content_html,
                    "thumb_media_id": thumb_media_id,
                    "need_open_comment": 0
                }
            ]
        }
        
        async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            
            if "media_id" in data:
                return data["media_id"]
            else:
                logger.error(f"Draft creation failed: {data}")
                return None

wechat_service = WechatService()
