import httpx
import logging
import time
import os
import json
from typing import Optional, Dict, Any
from app.utils.database import db

logger = logging.getLogger("gateway.wechat")

class WechatService:
    """微信公众号服务类 (云调用版 - 终极兼容)"""

    def __init__(self):
        # 确保 base_url 不带末尾斜杠
        self.base_url = "http://api.weixin.qq.com"
        self.service_name = os.getenv("K_SERVICE", "alwaysup")

    async def get_mp_appid(self, account_id: int) -> Optional[str]:
        """从数据库获取公众号 AppID"""
        query = "SELECT mp_appid FROM mp_account WHERE id = %s"
        res = await db.execute(query, (account_id,))
        if res:
            return res[0]['mp_appid']
        return None

    async def upload_image(self, account_id: int, image_path: str) -> Optional[str]:
        """上传素材 (严格路径匹配)"""
        appid = await self.get_mp_appid(account_id)
        if not appid:
            return None
            
        # 路径去掉开头的斜杠，尝试与网关匹配
        path = "cgi-bin/media/upload"
        url = f"{self.base_url}/{path}?type=image"
        
        headers = {
            "X-WX-APPID": appid,
            "X-WX-SERVICE": self.service_name
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(image_path, "rb") as f:
                files = {"media": ("cover.jpg", f, "image/jpeg")}
                # 显式打印我们要访问的完整 URL，方便日志比对
                logger.info(f"Accessing Cloud Call URL: {url}")
                resp = await client.post(url, files=files, headers=headers)
                data = resp.json()
                
                if "media_id" in data:
                    return data["media_id"]
                else:
                    logger.error(f"Media upload failed: {data}")
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
        """新建草稿 (严格路径匹配)"""
        appid = await self.get_mp_appid(account_id)
        if not appid:
            return None

        if not thumb_media_id:
            cover_path = await self._create_default_cover()
            thumb_media_id = await self.upload_image(account_id, cover_path)
            if not thumb_media_id:
                return None
            
        path = "cgi-bin/draft/add"
        url = f"{self.base_url}/{path}"
        
        headers = {
            "X-WX-APPID": appid,
            "X-WX-SERVICE": self.service_name,
            "Content-Type": "application/json"
        }
        
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
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, content=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers=headers)
            data = resp.json()
            
            if "media_id" in data:
                return data["media_id"]
            else:
                logger.error(f"Draft creation failed: {data}")
                return None

wechat_service = WechatService()
