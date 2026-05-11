import os
import smtplib
import logging
import asyncio
from email.mime.text import MIMEText
from email.header import Header

logger = logging.getLogger(__name__)

class EmailNotifier:
    """
    基于 SMTP 的标准邮件通知模块
    """

    @staticmethod
    def _send_sync(subject: str, content: str):
        """
        同步发送邮件逻辑
        """
        smtp_server = os.getenv("SMTP_SERVER", "smtp.qq.com")
        smtp_port = int(os.getenv("SMTP_PORT", 465))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASSWORD")
        receiver = os.getenv("SMTP_RECEIVER", smtp_user)

        if not all([smtp_user, smtp_pass, receiver]):
            logger.warning("SMTP configuration is incomplete. Skipping email notification.")
            return

        message = MIMEText(content, 'plain', 'utf-8')
        message['From'] = smtp_user
        message['To'] = receiver
        message['Subject'] = Header(subject, 'utf-8')

        try:
            # 使用 SSL 连接
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [receiver], message.as_string())
            logger.info(f"Email sent successfully: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    @classmethod
    async def send_report(cls, subject: str, content: str):
        """
        异步发送报告 (通过线程池包装)
        """
        await asyncio.to_thread(cls._send_sync, subject, content)

    @classmethod
    async def notify_success(cls, pipeline_name: str, trade_date: str, count: int):
        subject = f"✅ [SCF SUCCESS] {pipeline_name} - {trade_date}"
        content = f"任务执行成功！\n日期: {trade_date}\n采集数量: {count}\n状态: 已完成幂等落库并就绪。"
        await cls.send_report(subject, content)

    @classmethod
    async def notify_failure(cls, pipeline_name: str, trade_date: str, error_msg: str):
        subject = f"❌ [SCF FAILURE] {pipeline_name} - {trade_date}"
        content = f"任务执行失败！\n日期: {trade_date}\n错误详情: {error_msg}\n请及时检查云函数日志 (CLS)。"
        await cls.send_report(subject, content)
