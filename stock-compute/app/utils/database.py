import aiomysql
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self, prefix="DB"):
        self.host = os.getenv(f"{prefix}_HOST")
        self.port = int(os.getenv(f"{prefix}_PORT", 3306))
        self.user = os.getenv(f"{prefix}_USER")
        self.password = os.getenv(f"{prefix}_PASSWORD")
        self.db_name = os.getenv(f"{prefix}_NAME")
        self.pool = None

    async def connect(self):
        if not self.pool:
            self.pool = await aiomysql.create_pool(
                host=self.host, port=self.port,
                user=self.user, password=self.password,
                db=self.db_name, autocommit=True, charset='utf8mb4'
            )

    async def execute(self, sql, args=None):
        if not self.pool: await self.connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, args)
                return await cur.fetchall()

    async def fetch_val(self, sql, args=None):
        if not self.pool: await self.connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                res = await cur.fetchone()
                return res[0] if res else None

    async def fetch_one(self, sql, args=None):
        res = await self.execute(sql, args)
        return res[0] if res else None

    async def fetch_as_df(self, sql, args=None):
        if not self.pool: await self.connect()
        # aiomysql doesn't support pd.read_sql directly with pool
        async with self.pool.acquire() as conn:
            return pd.read_sql(sql, conn, params=args)

    async def insert_df(self, table, df):
        if df.empty: return
        cols = ",".join(df.columns)
        placeholders = ",".join(["%s"] * len(df.columns))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        args = [tuple(x) for x in df.values]
        await self.batch_insert_raw(sql, args)

    async def batch_insert_raw(self, sql, args):
        if not self.pool: await self.connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(sql, args)

    async def batch_insert(self, table, records: list):
        if not records: return
        df = pd.DataFrame(records)
        await self.insert_df(table, df)

# 云端与内网数据库实例
cloud_db = Database(prefix="CLOUD_DB")
internal_db = Database(prefix="INTERNAL_DB")
