import httpx
import logging
import time
import os
import json
from typing import Optional, Dict, Any
from app.utils.database import db

logger = logging.getLogger("gateway.wechat")

class WechatService:
    """微信公众号服务类 (云调用版 - 增强调试)"""

    def __init__(self):
        # 云托管内部调用地址
        self.base_url = "http://api.weixin.qq.com"
        # 自动识别云托管服务名
        self.service_name = os.getenv("K_SERVICE", "alwaysup")

    async def get_mp_appid(self, account_id: int) -> Optional[str]:
        """从数据库获取公众号 AppID"""
        query = "SELECT mp_appid FROM mp_account WHERE id = %s"
        res = await db.execute(query, (account_id,))
        if res:
            return res[0]['mp_appid']
        return None

    async def upload_image(self, account_id: int, image_path: str) -> Optional[str]:
        """上传永久素材(图片)"""
        appid = await self.get_mp_appid(account_id)
        if not appid:
            logger.error(f"Account {account_id} not found in DB")
            return None
            
        url = f"{self.base_url}/cgi-bin/material/add_material?type=image"
        
        headers = {
            "X-WX-APPID": appid,
            "X-WX-SERVICE": self.service_name
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(image_path, "rb") as f:
                files = {"media": ("cover.jpg", f, "image/jpeg")}
                resp = await client.post(url, files=files, headers=headers)
                data = resp.json()
                
                if "media_id" in data:
                    logger.info(f"Successfully uploaded material for AppID {appid}: {data['media_id']}")
                    return data["media_id"]
                else:
                    logger.error(f"Material upload failed for {appid}: {data}")
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
        """新建草稿 (带详细日志)"""
        appid = await self.get_mp_appid(account_id)
        if not appid:
            logger.error(f"Cannot find AppID for account_id {account_id}")
            return None

        # 1. 准备封面
        if not thumb_media_id:
            cover_path = await self._create_default_cover()
            thumb_media_id = await self.upload_image(account_id, cover_path)
            if not thumb_media_id:
                logger.error(f"Failed to prepare cover for AppID {appid}")
                return None
            
        # 2. 调用草稿箱接口
        url = f"{self.base_url}/cgi-bin/draft/add"
        
        headers = {
            "X-WX-APPID": appid,
            "X-WX-SERVICE": self.service_name,
            "Content-Type": "application/json"
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
        
        # 打印请求摘要（不打全文防止日志爆炸，只打长度和关键标识）
        logger.info(f"Sending draft to AppID {appid}, Content length: {len(content_html)}, Thumb: {thumb_media_id}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, content=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers=headers)
            data = resp.json()
            
            if "media_id" in data:
                logger.info(f"SUCCESS! Draft created in AppID {appid}. media_id: {data['media_id']}")
                return data["media_id"]
            else:
                logger.error(f"Draft creation failed for AppID {appid}. Response: {data}")
                return None

wechat_service = WechatService()
