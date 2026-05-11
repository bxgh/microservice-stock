import logging
import datetime
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate
import aiosmtplib
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("stock-manager.alerter")


class Alerter:
    """告警推送工具"""

    async def alert(self, level: str, title: str, context: Optional[Dict[str, Any]] = None):
        """发送告警邮件 (Async)"""
        subject = f"[{level}][{settings.SERVER_NAME}] {title}"

        # 根据级别选择主题颜色
        color_map = {
            "INFO": "#007bff",      # 蓝色
            "WARN": "#ffc107",      # 黄色
            "ERROR": "#dc3545",     # 红色
            "CRITICAL": "#343a40"   # 深灰色/黑色
        }
        theme_color = color_map.get(level, "#6c757d")

        # 构造详情行
        details_html = ""
        for k, v in (context or {}).items():
            # 如果值很长（比如包含了 HTML 表格），单独处理
            is_long_content = str(v).startswith("<div") or len(str(v)) > 200
            
            if is_long_content:
                # 长内容直接占据一整行，不使用两列布局
                details_html += f"""
                <tr>
                    <td colspan="2" style="padding: 10px; border: 1px solid #dee2e6; background-color: #f8f9fa; font-weight: bold;">{k}</td>
                </tr>
                <tr>
                    <td colspan="2" style="padding: 10px; border: 1px solid #dee2e6;">{v}</td>
                </tr>
                """
            else:
                details_html += f"""
                <tr>
                    <td class="label-td" style="padding: 10px; border: 1px solid #dee2e6; background-color: #f8f9fa; font-weight: bold; width: 90px; white-space: nowrap;">{k}</td>
                    <td class="value-td" style="padding: 10px; border: 1px solid #dee2e6; word-break: break-all;">{v}</td>
                </tr>
                """

        # HTML 模板
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                @media only screen and (max-width: 600px) {{
                    .container {{ width: 100% !important; border-radius: 0 !important; }}
                    .header {{ padding: 15px !important; }}
                    .content {{ padding: 15px !important; }}
                    .label-td {{ width: 80px !important; font-size: 13px !important; }}
                    .value-td {{ font-size: 13px !important; }}
                }}
            </style>
        </head>
        <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f7f9;">
            <div class="container" style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border-top: 5px solid {theme_color};">
                <div class="header" style="padding: 20px; background-color: {theme_color}; color: #fff;">
                    <h2 style="margin: 0; font-size: 18px;">{title}</h2>
                    <p style="margin: 5px 0 0; opacity: 0.8; font-size: 13px;">执行服务器: {settings.SERVER_NAME}</p>
                </div>
                <div class="content" style="padding: 20px;">
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px; table-layout: auto;">
                        <tr>
                            <td class="label-td" style="padding: 10px; border: 1px solid #dee2e6; background-color: #f8f9fa; font-weight: bold; width: 90px; white-space: nowrap;">告警级别</td>
                            <td class="value-td" style="padding: 10px; border: 1px solid #dee2e6; color: {theme_color}; font-weight: bold;">{level}</td>
                        </tr>
                        <tr>
                            <td class="label-td" style="padding: 10px; border: 1px solid #dee2e6; background-color: #f8f9fa; font-weight: bold; white-space: nowrap;">发生时间</td>
                            <td class="value-td" style="padding: 10px; border: 1px solid #dee2e6; word-break: break-all;">{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                        </tr>
                        {details_html}
                    </table>
                    <div style="padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107; color: #856404; font-size: 12px; border-radius: 4px;">
                        <strong>温馨提示:</strong> 请系统管理员及时关注并处理相关任务状态。
                    </div>
                </div>
                <div style="padding: 15px; background-color: #f8f9fa; text-align: center; font-size: 11px; color: #999; border-top: 1px solid #eee;">
                    本邮件由 [{settings.SERVER_NAME}] 系统自动发出，请勿直接回复。
                </div>
            </div>
        </body>
        </html>
        """

        msg = MIMEText(html_content, "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.ALERT_RECEIVER
        msg["Date"] = formatdate(localtime=True)

        # 记录概要
        logger.debug(f"【邮件正文预览】Subject: {subject}\nBody Preview: {html_content[:500]}...")

        try:
            if settings.SMTP_USER and settings.SMTP_PASS:
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
            else:
                logger.info(f"未配置 SMTP，跳过邮件发送 (但已记录日志预览)")
        except Exception as e:
            logger.error(f"告警邮件发送失败: {e}")


alerter = Alerter()
