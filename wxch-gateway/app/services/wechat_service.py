import httpx
import logging
import time
from typing import Optional, Dict, Any
from app.utils.database import db

logger = logging.getLogger("gateway.wechat")

class WechatService:
    """微信公众号服务类，处理 AccessToken 及草稿箱同步"""

    async def get_access_token(self, account_id: int) -> Optional[str]:
        """获取有效的 AccessToken (带缓存逻辑)"""
        # 1. 查库获取当前 Token 及 AppSecret
        # 注意：这里假设 mp_account 表已经新增了 mp_appsecret 字段
        query = """
            SELECT mp_appid, mp_appsecret, access_token_encrypted, access_token_expires_at 
            FROM mp_account WHERE id = %s
        """
        res = await db.execute(query, (account_id,))
        if not res:
            return None
        
        row = res[0]
        now = int(time.time())
        
        # 2. 检查 Token 是否未过期 (预留 5 分钟缓冲)
        if row['access_token_encrypted'] and row['access_token_expires_at']:
            expires_at = int(row['access_token_expires_at'].timestamp())
            if expires_at > now + 300:
                return row['access_token_encrypted'] # 暂时当做明文处理，除非有加密逻辑
        
        # 3. 如果已过期或不存在，向微信请求
        appid = row['mp_appid']
        secret = row.get('mp_appsecret') # 需要确保有这个字段
        
        if not secret:
            logger.error(f"Account {account_id} has no AppSecret configured")
            return None
            
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            data = resp.json()
            
            if "access_token" in data:
                token = data["access_token"]
                expires_in = data["expires_in"]
                
                # 4. 更新数据库
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

    async def add_draft(self, account_id: int, title: str, content_html: str, 
                        author: str = "", digest: str = "", thumb_media_id: str = "") -> Optional[str]:
        """新建草稿"""
        token = await self.get_access_token(account_id)
        if not token:
            return None
            
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
        
        # 微信草稿箱数据结构
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
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            
            if "media_id" in data:
                return data["media_id"]
            else:
                logger.error(f"Failed to add draft: {data}")
                return None

wechat_service = WechatService()
