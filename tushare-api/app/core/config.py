from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    TUSHARE_TOKEN: str
    LOG_LEVEL: str = "INFO"
    
    # 允许通过 .env 文件加载
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
