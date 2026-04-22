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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True
    )

settings = Settings()
