import os
import asyncio
import logging
import aiomysql
from typing import Optional

logger = logging.getLogger(__name__)

class DBManager:
    """
    异步数据库连接管理器 (针对 SCF 优化)
    """
    _pool: Optional[aiomysql.Pool] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_pool(cls) -> aiomysql.Pool:
        """
        获取连接池 (针对 SCF 优化的单例模式)
        """
        current_loop = asyncio.get_running_loop()
        
        # 核心修复：检查现有池是否绑定在已关闭或不同的 Loop 上
        if cls._pool is not None:
            if cls._pool._loop != current_loop or cls._pool._loop.is_closed():
                logger.info("Event loop changed or closed. Resetting database pool.")
                cls._pool = None

        if cls._pool is not None:
            return cls._pool

        async with cls._lock:
            if cls._pool is not None:
                return cls._pool

            # 从环境变量获取配置
            host = os.getenv("MYSQL_HOST", "localhost")
            port = int(os.getenv("MYSQL_PORT", 3306))
            user = os.getenv("MYSQL_USER", "root")
            password = os.getenv("MYSQL_PASSWORD", "")
            db = os.getenv("MYSQL_DB", "stock")

            logger.info(f"Connecting to MySQL at {host}:{port}...")
            
            # 连接重试逻辑
            for attempt in range(3):
                try:
                    cls._pool = await aiomysql.create_pool(
                        host=host,
                        port=port,
                        user=user,
                        password=password,
                        db=db,
                        autocommit=True,
                        minsize=1,
                        maxsize=5,
                        connect_timeout=10,
                        # 核心配置：回收超过 1 小时的连接，防止 Broken Pipe
                        pool_recycle=3600
                    )
                    logger.info("MySQL connection pool created successfully.")
                    return cls._pool
                except Exception as e:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                    if attempt < 2:
                        await asyncio.sleep(2)
                    else:
                        logger.error("Could not connect to MySQL after 3 attempts.")
                        raise

    @classmethod
    async def close_pool(cls):
        """
        关闭连接池
        """
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
            logger.info("MySQL connection pool closed.")

async def execute_query(sql: str, params: tuple = None, is_select: bool = True):
    """
    带重试机制的查询执行器
    """
    pool = await DBManager.get_pool()
    
    for attempt in range(2):
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(sql, params)
                    if is_select:
                        return await cur.fetchall()
                    else:
                        return cur.rowcount
        except (aiomysql.OperationalError, aiomysql.InternalError) as e:
            # 针对 Serverless 常见的连接失效进行重连
            logger.warning(f"SQL execution failed (attempt {attempt + 1}): {e}")
            if attempt == 0:
                # 尝试重新创建连接池
                await DBManager.close_pool()
                pool = await DBManager.get_pool()
            else:
                raise
