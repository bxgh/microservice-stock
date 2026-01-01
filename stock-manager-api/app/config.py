import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用配置"""
    
    # 数据库配置
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "stock_data")
    
    # 其他容器 URL
    BAOSTOCK_API_URL: str = os.getenv("BAOSTOCK_API_URL", "http://baostock-api:8000")
    AKSHARE_API_URL: str = os.getenv("AKSHARE_API_URL", "http://akshare-api:8000")
    PYWENCAI_API_URL: str = os.getenv("PYWENCAI_API_URL", "http://pywencai-api:8000")
    
    # 日志级别
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        case_sensitive = True

settings = Settings()
