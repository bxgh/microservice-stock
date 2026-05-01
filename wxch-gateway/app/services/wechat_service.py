import httpx
import logging
import time
import os
from typing import Optional, Dict, Any
from app.utils.database import db

logger = logging.getLogger("gateway.wechat")

class WechatService:
    """微信公众号服务类 (云调用版)"""

    def __init__(self):
        # 云托管内部调用地址，无需 access_token
        self.base_url = "http://api.weixin.qq.com"

    async def get_mp_appid(self, account_id: int) -> Optional[str]:
        """从数据库获取公众号 AppID"""
        query = "SELECT mp_appid FROM mp_account WHERE id = %s"
        res = await db.execute(query, (account_id,))
        if res:
            return res[0]['mp_appid']
        return None

    async def upload_image(self, account_id: int, image_path: str) -> Optional[str]:
        """上传永久素材(图片) - 云调用版"""
        appid = await self.get_mp_appid(account_id)
        if not appid:
            logger.error(f"Account {account_id} not found")
            return None
            
        # 云调用 URL 格式：直接去掉 access_token 参数
        url = f"{self.base_url}/cgi-bin/material/add_material?type=image"
        
        headers = {
            "X-WX-APPID": appid
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(image_path, "rb") as f:
                files = {"media": ("cover.jpg", f, "image/jpeg")}
                resp = await client.post(url, files=files, headers=headers)
                data = resp.json()
                
                if "media_id" in data:
                    return data["media_id"]
                else:
                    logger.error(f"Cloud Call upload failed: {data}")
                    return None

    async def _create_default_cover(self) -> str:
        """生成默认封面图"""
        from PIL import Image, ImageDraw
        path = "temp_cover.jpg"
        # 使用深色调符合 Fintech 风格
        img = Image.new('RGB', (900, 383), color=(40, 44, 52))
        d = ImageDraw.Draw(img)
        # 画一个简单的金色边框
        d.rectangle([10, 10, 890, 373], outline=(212, 167, 106), width=3)
        img.save(path)
        return path

    async def add_draft(self, account_id: int, title: str, content_html: str, 
                        author: str = "八仙过海", digest: str = "", thumb_media_id: str = "") -> Optional[str]:
        """新建草稿 - 云调用版"""
        appid = await self.get_mp_appid(account_id)
        if not appid:
            return None

        # 1. 如果没有封面，先自动生成并上传
        if not thumb_media_id:
            cover_path = await self._create_default_cover()
            thumb_media_id = await self.upload_image(account_id, cover_path)
            if not thumb_media_id:
                logger.error("Failed to get thumb_media_id via Cloud Call")
                return None
            
        # 2. 云调用添加草稿
        url = f"{self.base_url}/cgi-bin/draft/add"
        
        headers = {
            "X-WX-APPID": appid
        }
        
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
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            data = resp.json()
            
            if "media_id" in data:
                return data["media_id"]
            else:
                logger.error(f"Cloud Call add_draft failed: {data}")
                return None

wechat_service = WechatService()
