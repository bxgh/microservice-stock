import logging
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.config import settings

logger = logging.getLogger("stock-manager.fund")

class FundService:
    def __init__(self):
        self.akshare_url = settings.AKSHARE_API_URL
        # 核心 ETF 名单 (代码, 名称)
        self.CORE_ETFS = [
            ('510050.SH', '上证50ETF'),
            ('510300.SH', '沪深300ETF'),
            ('510500.SH', '中证500ETF'),
            ('512100.SH', '中证1000ETF'),
            ('588000.SH', '科创50ETF'),
            ('159915.SZ', '创业板ETF'),
            ('513100.SH', '纳指ETF'),
            ('510900.SH', 'H股ETF'),
            ('159941.SZ', '纳指ETF'),
            ('512660.SH', '军工ETF'),
            ('512010.SH', '医药ETF'),
            ('512800.SH', '银行ETF'),
            ('512880.SH', '证券ETF')
        ]

    async def sync_fund_basic(self):
        """同步核心 ETF 基础信息 (硬编码注入)"""
        try:
            logger.info("开始同步核心 ETF 基础信息")
            query = """
                INSERT INTO fund_basic (ts_code, symbol, name, fund_type, is_core)
                VALUES (%s, %s, %s, 'ETF', 1)
                ON DUPLICATE KEY UPDATE name=VALUES(name), is_core=1
            """
            args = [(c[0], c[0].split('.')[0], c[1]) for c in self.CORE_ETFS]
            await db.execute_many(query, args)
            logger.info(f"核心 ETF 列表注入完成: {len(args)} 条")
            return len(args)
        except Exception as e:
            logger.error(f"同步核心基金列表失败: {e}")
            return 0

    async def sync_fund_daily(self, ts_code: str, trade_date: str = None):
        """从 AkShare 代理同步 ETF 日线行情"""
        try:
            symbol = ts_code.split('.')[0]
            url = f"{self.akshare_url}/api/v1/fund/etf_daily"
            params = {"symbol": symbol}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            if not data: return 0

            query = """
                INSERT INTO fund_daily (
                    ts_code, trade_date, open, high, low, close, vol, amount
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    open=VALUES(open), high=VALUES(high), low=VALUES(low), close=VALUES(close)
            """
            
            args = []
            for i in data:
                dt = i.get("date")
                if trade_date and dt != trade_date:
                    continue
                    
                args.append((
                    ts_code, dt, i.get("open"), i.get("high"),
                    i.get("low"), i.get("close"), i.get("volume"), i.get("amount")
                ))

            if args:
                await db.execute_many(query, args)
            return len(args)
            
        except Exception as e:
            logger.error(f"同步 ETF 行情失败 ({ts_code}): {e}")
            return 0

    async def backfill_history(self, ts_code: str):
        """回补历史数据 (实际上 sync_fund_daily 已抓取全量历史)"""
        return await self.sync_fund_daily(ts_code=ts_code)

fund_service = FundService()
