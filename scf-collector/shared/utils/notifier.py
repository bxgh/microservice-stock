import os
import logging
import asyncio
import datetime
from zoneinfo import ZoneInfo
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formatdate
import httpx
from typing import Dict, Any, Optional
import aiosmtplib

logger = logging.getLogger(__name__)

class WeChatNotifier:
    """
    微信通知模块：支持 Server酱 (SCT) 和 企业微信 Webhook
    """
    
    @staticmethod
    async def send_msg(title: str, content: str):
        """
        发送微信通知
        """
        # 1. 尝试 Server酱 (SCT_KEY)
        sct_key = os.getenv("SCT_KEY")
        if sct_key:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"https://sctapi.ftqq.com/{sct_key}.send",
                        data={"title": title, "desp": content}
                    )
                    if resp.status_code == 200:
                        logger.info(f"ServerChan notification sent: {title}")
                        return True
            except Exception as e:
                logger.error(f"Failed to send ServerChan notification: {e}")

        # 2. 尝试 企业微信 Webhook (WX_WEBHOOK)
        wx_webhook = os.getenv("WX_WEBHOOK")
        if wx_webhook:
            try:
                async with httpx.AsyncClient() as client:
                    data = {
                        "msgtype": "markdown",
                        "markdown": {
                            "content": f"### {title}\n{content}"
                        }
                    }
                    resp = await client.post(wx_webhook, json=data)
                    if resp.status_code == 200:
                        logger.info(f"WorkWeChat notification sent: {title}")
                        return True
            except Exception as e:
                logger.error(f"Failed to send WorkWeChat notification: {e}")
        
        logger.warning("WeChat notification keys are missing or failed.")
        return False

class EmailNotifier:
    """
    基于 aiosmtplib 的异步邮件通知模块 (复用 CVM Alerter 逻辑)
    """

    @staticmethod
    async def send_report(level: str, title: str, context: Optional[Dict[str, Any]] = None):
        """
        发送 HTML 格式的异步告警邮件
        """
        smtp_server = os.getenv("SMTP_SERVER", "smtp.qq.com")
        smtp_port = int(os.getenv("SMTP_PORT", 465))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASSWORD")
        receiver = os.getenv("SMTP_RECEIVER", smtp_user)
        server_name = os.getenv("SERVER_NAME", "SCF-Collector")

        if not all([smtp_user, smtp_pass, receiver]):
            logger.warning("SMTP configuration is incomplete. Skipping email notification.")
            return

        # 根据级别选择主题颜色
        color_map = {
            "INFO": "#007bff",      # 蓝色
            "SUCCESS": "#28a745",   # 绿色
            "WARN": "#ffc107",      # 黄色
            "ERROR": "#dc3545",     # 红色
        }
        theme_color = color_map.get(level, "#6c757d")

        # 构造详情行
        details_html = ""
        if context:
            for k, v in context.items():
                details_html += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #dee2e6; background-color: #f8f9fa; font-weight: bold; width: 90px; white-space: nowrap;">{k}</td>
                    <td style="padding: 10px; border: 1px solid #dee2e6; word-break: break-all;">{v}</td>
                </tr>
                """

        # HTML 模板
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f7f9;">
            <div style="max-width: 600px; margin: 20px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border-top: 5px solid {theme_color};">
                <div style="padding: 20px; background-color: {theme_color}; color: #fff;">
                    <h2 style="margin: 0; font-size: 18px;">{title}</h2>
                    <p style="margin: 5px 0 0; opacity: 0.8; font-size: 13px;">执行环境: {server_name}</p>
                </div>
                <div style="padding: 20px;">
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px;">
                        <tr>
                            <td style="padding: 10px; border: 1px solid #dee2e6; background-color: #f8f9fa; font-weight: bold; width: 90px;">状态</td>
                            <td style="padding: 10px; border: 1px solid #dee2e6; color: {theme_color}; font-weight: bold;">{level}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #dee2e6; background-color: #f8f9fa; font-weight: bold;">发生时间</td>
                            <td style="padding: 10px; border: 1px solid #dee2e6;">{datetime.datetime.now(ZoneInfo("Asia/Shanghai")).strftime('%Y-%m-%d %H:%M:%S')}</td>
                        </tr>
                        {details_html}
                    </table>
                </div>
                <div style="padding: 15px; background-color: #f8f9fa; text-align: center; font-size: 11px; color: #999; border-top: 1px solid #eee;">
                    本邮件由 [{server_name}] 系统自动发出，请勿回复。
                </div>
            </div>
        </body>
        </html>
        """

        msg = MIMEText(html_content, "html", "utf-8")
        msg["Subject"] = Header(title, "utf-8")
        msg["From"] = smtp_user
        msg["To"] = receiver
        msg["Date"] = formatdate(localtime=True)

        try:
            await aiosmtplib.send(
                msg,
                hostname=smtp_server,
                port=smtp_port,
                username=smtp_user,
                password=smtp_pass,
                use_tls=True,
                timeout=10
            )
            logger.info(f"Notification email sent: {title}")
        except Exception as e:
            logger.error(f"Failed to send notification email: {e}")

    @classmethod
    async def notify_success(cls, pipeline_name: str, trade_date: str, count: int, table_name: str = "N/A", extra: Dict[str, Any] = None):
        title = f"✅ 任务成功: {pipeline_name}"
        context = {
            "业务名称": pipeline_name,
            "业务表名": table_name,
            "业务日期": trade_date,
            "采集数量": f"{count} 条",
            "执行状态": "Success / Idempotent"
        }
        if extra:
            context.update(extra)
        await cls.send_report("SUCCESS", title, context)

    @classmethod
    async def notify_failure(cls, pipeline_name: str, trade_date: str, error_msg: str):
        title = f"❌ 任务失败: {pipeline_name}"
        context = {
            "业务日期": trade_date,
            "错误详情": error_msg,
            "状态": "Critical Error"
        }
        await cls.send_report("ERROR", title, context)
