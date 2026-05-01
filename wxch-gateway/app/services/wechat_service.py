import httpx
import logging
import time
import os
import json
from typing import Optional, Dict, Any
from app.utils.database import db

logger = logging.getLogger("gateway.wechat")

class WechatService:
    """微信公众号服务类 (云调用版 - 终极尝试)"""

    def __init__(self):
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
        """上传素材 (切回永久素材模式)"""
        appid = await self.get_mp_appid(account_id)
        if not appid:
            return None
            
        # 在白名单已通的前提下，重新尝试永久素材接口，因为草稿箱可能强制要求永久封面
        path = "cgi-bin/material/add_material"
        url = f"{self.base_url}/{path}?type=image"
        
        headers = {
            "X-WX-APPID": appid,
            "X-WX-SERVICE": self.service_name
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(image_path, "rb") as f:
                files = {"media": ("cover.jpg", f, "image/jpeg")}
                logger.info(f"Trying Permanent Material Upload: {url}")
                resp = await client.post(url, files=files, headers=headers)
                data = resp.json()
                
                if "media_id" in data:
                    logger.info(f"Permanent Material Upload SUCCESS: {data['media_id']}")
                    return data["media_id"]
                else:
                    logger.error(f"Permanent Material Upload FAILED: {data}")
                    # 如果永久素材还是报 48001，尝试兜底到临时素材
                    logger.info("Falling back to Temp Material Upload...")
                    temp_url = f"{self.base_url}/cgi-bin/media/upload?type=image"
                    f.seek(0)
                    resp_temp = await client.post(temp_url, files={"media": ("cover.jpg", f, "image/jpeg")}, headers=headers)
                    data_temp = resp_temp.json()
                    if "media_id" in data_temp:
                        logger.info(f"Temp Material Upload SUCCESS: {data_temp['media_id']}")
                        return data_temp["media_id"]
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
        """新建草稿"""
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
                logger.info(f"DRAFT CREATION SUCCESS: {data['media_id']}")
                return data["media_id"]
            else:
                logger.error(f"DRAFT CREATION FAILED: {data}")
                return None

wechat_service = WechatService()
