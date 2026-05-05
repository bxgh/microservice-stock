import pandas as pd
from datetime import date, timedelta
from app.utils.logger import get_logger
from app.utils.database import cloud_db, internal_db

logger = get_logger("stock-compute.sync")

class CloudDataSyncer:
    """云端 -> 内网 MySQL 副本 增量同步 (E4)"""

    SYNC_TABLES = {
        "ods_kline_daily":          ("trade_date", 90),
        "ads_l1_market_overview":   ("trade_date", 60),
        "ods_l3_capital_flow":      ("trade_date", 30),
        "ods_l4_sentiment":         ("biz_date",   30),
        "ads_l8_unified_signal":    ("biz_date",   30),
        "ods_l6_event":             ("biz_date",   30),
        "ads_l2_structural":        ("biz_date",   30),
        "ods_etf_kline":            ("trade_date", 60),
    }

    FULL_SYNC_TABLES = [
        "meta_stock_basic",
        "meta_industry_mapping",
        "meta_concept_mapping",
        "meta_trading_calendar",
    ]

    async def sync_for_compute(self, biz_date: date):
        """计算前的同步流程 (E4-S2)"""
        # 1. 全量同步元数据
        for table in self.FULL_SYNC_TABLES:
            await self._sync_full(table)

        # 2. 增量同步行情数据
        for table, (date_field, retain) in self.SYNC_TABLES.items():
            # 获取本地最大日期
            local_max = await self._get_local_max_date(table, date_field)
            start = (local_max + timedelta(days=1)) if local_max else (biz_date - timedelta(days=retain))
            
            if start > biz_date:
                continue
                
            logger.info(f"正在同步 {table}: {start} -> {biz_date}")
            await self._sync_incremental(table, date_field, start, biz_date)
            
            # 清理旧数据
            await self._purge_old(table, date_field, retain)

    async def _get_local_max_date(self, table, date_field):
        sql = f"SELECT MAX({date_field}) FROM {table}"
        return await internal_db.fetch_val(sql)

    async def _sync_full(self, table):
        # 简单全量同步：删除后重新写入
        logger.info(f"全量同步元数据表: {table}")
        df = await cloud_db.fetch_as_df(f"SELECT * FROM {table}")
        if not df.empty:
            await internal_db.execute(f"DELETE FROM {table}")
            await internal_db.insert_df(table, df)

    async def _sync_incremental(self, table, date_field, start, end):
        current = start
        while current <= end:
            df = await cloud_db.fetch_as_df(f"SELECT * FROM {table} WHERE {date_field}=%s", (current,))
            if not df.empty:
                await internal_db.insert_df(table, df)
            current += timedelta(days=1)

    async def _purge_old(self, table, date_field, retain_days):
        cutoff = date.today() - timedelta(days=retain_days)
        await internal_db.execute(f"DELETE FROM {table} WHERE {date_field} < %s", (cutoff,))
