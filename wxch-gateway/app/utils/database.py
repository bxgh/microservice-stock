import aiomysql
from app.config import settings
import logging

logger = logging.getLogger("gateway.database")

class Database:
    """MySQL 异步连接池管理"""
    def __init__(self):
        self.pool = None

    async def connect(self):
        """初始化连接池"""
        if self.pool is None:
            try:
                self.pool = await aiomysql.create_pool(
                    host=settings.DB_HOST,
                    port=settings.DB_PORT,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    db=settings.DB_NAME,
                    minsize=1,
                    maxsize=10,
                    autocommit=True,
                    charset='utf8mb4'
                )
                logger.info("MySQL 异步连接池初始化完成")
            except Exception as e:
                logger.error(f"MySQL 连接池初始化失败: {e}")
                raise e

    async def disconnect(self):
        """关闭连接池"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("MySQL 异步连接池已关闭")

    async def execute(self, query: str, args: tuple = None):
        """执行单条 SQL"""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                return await cur.fetchall()

# 全局数据库对象
db = Database()
