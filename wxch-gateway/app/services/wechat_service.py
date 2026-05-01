import httpx
import logging
import time
import os
from typing import Optional, Dict, Any
from app.utils.database import db

logger = logging.getLogger("gateway.wechat")

class WechatService:
    """微信公众号服务类 (白名单模式 - 恢复版)"""

    def __init__(self):
        # 恢复公网地址
        self.base_url = "https://api.weixin.qq.com"

    async def get_access_token(self, account_id: int) -> Optional[str]:
        """获取有效的 AccessToken (从数据库获取并检查过期)"""
        query = "SELECT mp_appid, access_token_encrypted, access_token_expires_at FROM mp_account WHERE id = %s"
        res = await db.execute(query, (account_id,))
        if not res:
            return None
        
        account = res[0]
        # 注意：这里假设 access_token_encrypted 存的是明文或通过某种方式可解密
        # 为简化逻辑，目前直接使用。如果生产环境有加解密逻辑，请在此处扩展。
        token = account['access_token_encrypted']
        expires_at = account['access_token_expires_at']
        
        # 简单的过期校验 (提前 5 分钟刷新)
        if token and expires_at and expires_at.timestamp() > time.time() + 300:
            return token
            
        # 如果过期，此处理论上应有自动刷新逻辑，但受限于个人号可能无法自动刷新
        # 建议用户通过后台或工具手动更新此字段
        return token

    async def upload_image(self, account_id: int, image_path: str) -> Optional[str]:
        """上传素材 (优先尝试临时素材，兼容性更广)"""
        token = await self.get_access_token(account_id)
        if not token:
            logger.error("No valid AccessToken found")
            return None
            
        url = f"{self.base_url}/cgi-bin/media/upload?access_token={token}&type=image"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(image_path, "rb") as f:
                files = {"media": ("cover.jpg", f, "image/jpeg")}
                resp = await client.post(url, files=files)
                data = resp.json()
                
                if "media_id" in data:
                    return data["media_id"]
                else:
                    logger.error(f"Material upload failed (Whitelist mode): {data}")
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
        """新建草稿 (白名单模式)"""
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
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            
            if "media_id" in data:
                return data["media_id"]
            else:
                logger.error(f"Draft creation failed (Whitelist mode): {data}")
                return None

wechat_service = WechatService()
