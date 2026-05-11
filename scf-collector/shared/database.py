import os
import time
import logging
from sqlalchemy import create_all_engines, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

# 从环境变量获取配置
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "stock_serverless")

# 针对 Serverless 数据库优化的连接字符串
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# 创建引擎
# pool_pre_ping=True: 每次从池中取连接都会先检查是否有效，适合 Serverless 休眠场景
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db_session():
    """获取数据库会话，带有简单的唤醒重试逻辑"""
    retries = 3
    while retries > 0:
        try:
            db = SessionLocal()
            # 简单测试连接
            db.execute("SELECT 1")
            return db
        except OperationalError as e:
            retries -= 1
            logger.warning(f"Database connection failed, retrying... ({retries} left). Error: {e}")
            if retries == 0:
                raise e
            time.sleep(5) # 等待 5 秒让 Serverless 数据库唤醒
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            raise e
