import logging
import asyncio
import datetime
from email.mime.text import MIMEText
from email.utils import formatdate
import aiosmtplib
from app.config import settings

logger = logging.getLogger("stock-manager.alerter")

class Alerter:
    """系统告警器"""
    
    LEVELS = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3, "CRITICAL": 4}
    
    _instance = None
    _dedup_cache = {} # 简单内存防抖

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Alerter, cls).__new__(cls)
        return cls._instance

    async def alert(self, level: str, title: str, context: dict = None):
        """发送告警"""
        # 1. 始终写入日志
        log_msg = f"【告警-{level}】{title} | {context or ''}"
        if level == "CRITICAL":
            logger.critical(log_msg)
        elif level == "ERROR":
            logger.error(log_msg)
        elif level == "WARN":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        # 2. 检查配置与级别阈值
        if not settings.SMTP_USER or not settings.SMTP_PASS or not settings.ALERT_RECEIVER:
            return

        threshold = self.LEVELS.get(settings.ALERT_LEVEL_THRESHOLD, 2)
        if self.LEVELS.get(level, 0) < threshold:
            return

        # 3. 防抖逻辑 (5分钟内相同标题不重复发送)
        cache_key = f"{level}:{title}"
        now = datetime.datetime.now()
        if cache_key in self._dedup_cache:
            if (now - self._dedup_cache[cache_key]).total_seconds() < 300:
                return
        self._dedup_cache[cache_key] = now

        # 4. 发送邮件
        await self._send_email(level, title, context)

    async def _send_email(self, level, title, context):
        """异步发送邮件"""
        subject = f"[{level}][stock-system] {title}"
        
        # 渲染正文
        ctx_str = "\n".join([f"- {k}: {v}" for k, v in (context or {}).items()])
        body = f"""
股票调度系统告警通知
---------------------------------------
级别: {level}
时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
标题: {title}

上下文详情:
{ctx_str if ctx_str else '无'}

请及时处理。
---------------------------------------
(自动发送，请勿回复)
"""
        
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.ALERT_RECEIVER
        msg["Date"] = formatdate(localtime=True)

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASS,
                use_tls=True,
                timeout=10
            )
            logger.info(f"告警邮件发送成功: {title}")
        except Exception as e:
            logger.error(f"告警邮件发送失败: {e}")

# 全局单例
alerter = Alerter()
