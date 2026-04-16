import aiomysql
import logging
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monitor-service.database")

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if self.pool is None:
            try:
                self.pool = await aiomysql.create_pool(
                    host=settings.DB_HOST,
                    port=settings.DB_PORT,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    db=settings.DB_NAME,
                    autocommit=True,
                    charset='utf8mb4'
                )
                logger.info("MySQL 异步连接池初始化完成 (monitor-service)")
            except Exception as e:
                logger.error(f"MySQL 连接池初始化失败: {e}")
                raise e

    async def disconnect(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

    async def execute(self, query: str, args: tuple = None):
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                return await cur.fetchall()

    async def execute_many(self, query: str, args: list):
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                return await cur.executemany(query, args)

db = Database()
