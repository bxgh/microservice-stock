from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "stock_data"

    # 其他容器 URL
    BAOSTOCK_API_URL: str = "http://baostock-api:8000"
    AKSHARE_API_URL: str = "http://akshare-api:8000"
    TUSHARE_API_URL: str = "http://tushare-api:8000"
    PYWENCAI_API_URL: str = "http://pywencai-api:8000"
    MONITOR_SERVICE_URL: str = "http://monitor-service:8000"

    # 日志级别
    LOG_LEVEL: str = "INFO"

    # 邮件告警配置
    SMTP_HOST: str = "smtp.qq.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    ALERT_RECEIVER: str = ""
    ALERT_LEVEL_THRESHOLD: str = "INFO"
    SERVER_NAME: str = "Tencent Cloud - Node-Cloud"

    model_config = SettingsConfigDict(
        env_file="../.env",
        extra="ignore",
        case_sensitive=True
    )


settings = Settings()
