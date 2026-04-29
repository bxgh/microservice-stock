from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """应用配置"""
    
    # 数据库配置
    DB_HOST: str = "172.17.0.10"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "alwaysup@888"
    DB_NAME: str = "alwaysup"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    TZ: str = "Asia/Shanghai"
    
    # 微信小程序配置
    WECHAT_APPID: str = "your_appid_here"
    WECHAT_SECRET: str = "your_secret_here"
    
    # JWT配置
    JWT_SECRET: str = "your_jwt_secret_here_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_DAYS: int = 30
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True
    )

settings = Settings()
