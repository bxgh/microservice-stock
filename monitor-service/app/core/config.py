import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 数据库配置
    DB_HOST: str = os.getenv("DB_HOST", "mysql-stock")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "stock123")
    DB_NAME: str = os.getenv("DB_NAME", "stock_data")

    # API 内部 URL
    AKSHARE_API_URL: str = os.getenv("AKSHARE_API_URL", "http://akshare-api:8003/api/v1")
    
    # 监控配置
    # ETF 篮子配置 (JSON 字符串或列表)
    GROWTH_ETFS: list = ["512760", "512480", "516160", "512010", "588000"] # 科技、半导体、光伏、医疗、科创50
    VALUE_ETFS: list = ["512200", "512800", "512690", "511010"] # 房地产、银行、白酒、基建
    
    # 时序指数
    INDEX_LIST: list = ["000300", "000852", "000001"] # 沪深300, 中证1000, 上证指数
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
