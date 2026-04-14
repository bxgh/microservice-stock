
import asyncio
import datetime
import time
from typing import Dict, Any, List, Optional
import akshare as ak
from app.utils.logger import get_logger
from app.utils.database import db

logger = get_logger("akshare-api.etf_service")

class EtfService:
    """ETF 数据服务"""

    def __init__(self):
        self._sync_status = {
            "running": False,
            "total": 0,
            "current": 0,
            "start_time": 0
        }
        self.lock = asyncio.Lock()

    async def get_all_etfs(self) -> List[Dict[str, str]]:
        """获取全市场 ETF 列表"""
        try:
            # specifically for fund_etf_spot_em which returns a DataFrame
            df = await asyncio.to_thread(ak.fund_etf_spot_em)
            if df is None or df.empty:
                return []
            
            # format: 代码, 名称, ...
            # Need to map to standard format (sh.51xxxx, sz.15xxxx)
            result = []
            for _, row in df.iterrows():
                code = str(row['代码'])
                name = str(row['名称'])
                
                # Determine market prefix
                prefix = ""
                if code.startswith("5"):
                    prefix = "sh"
                elif code.startswith("1"):
                    prefix = "sz"
                else:
                    # e.g., 3xxxx might be LOF, but we focus on ETF
                    continue
                
                std_code = f"{prefix}.{code}"
                result.append({"code": std_code, "name": name})
                
            return result
        except Exception as e:
            logger.error(f"获取ETF列表失败: {e}")
            return []

    async def sync_etf_daily(self) -> Dict[str, Any]:
        """ETF 日线增量同步"""
        async with self.lock:
            if self._sync_status["running"]:
                return {"status": "running", "message": "任务已在运行"}
            self._sync_status["running"] = True
            self._sync_status["start_time"] = time.time()

        try:
            etfs = await self.get_all_etfs()
            logger.info(f"获取到 {len(etfs)} 只ETF，开始同步...")
            
            self._sync_status["total"] = len(etfs)
            self._sync_status["current"] = 0
            
            updated_count = 0
            
            for index, etf in enumerate(etfs):
                code = etf["code"]
                try:
                    await self._sync_single_etf(code)
                    updated_count += 1
                except Exception as e:
                    logger.error(f"同步ETF {code} 失败: {e}")
                
                self._sync_status["current"] = index + 1
                if (index + 1) % 50 == 0:
                     logger.info(f"ETF同步进度: {index+1}/{len(etfs)}")
                     
            duration = time.time() - self._sync_status["start_time"]
            return {
                "status": "success",
                "total": len(etfs),
                "updated": updated_count,
                "duration_seconds": int(duration)
            }
        except Exception as e:
            logger.error(f"ETF全量同步异常: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            async with self.lock:
                self._sync_status["running"] = False

    async def _sync_single_etf(self, std_code: str):
        """同步单只 ETF"""
        # Split sh.510050 -> 510050
        symbol = std_code.split(".")[1]
        
        # Determine start date
        start_date = "20000101"
        try:
            # Check latest date in DB
            res = await db.execute("SELECT MAX(trade_date) FROM stock_kline_daily WHERE code=%s", (std_code,))
            if res and res[0][0]:
                last_date = res[0][0] # datetime.date
                start_date = (last_date + datetime.timedelta(days=1)).strftime("%Y%m%d")
                
                # If already today, skip
                if last_date >= datetime.date.today():
                    return
        except Exception as e:
            logger.warning(f"查询 {std_code} 最新日期失败，默认全量: {e}")

        # Fetch Data
        try:
            df = await asyncio.to_thread(
                ak.fund_etf_hist_em,
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date="20500101",
                adjust="qfq"
            )
        except Exception as e:
            # e.g., "indices are out of bounds" means no data
            return

        if df is None or df.empty:
            return

        # Prepare for DB
        # Columns: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
        rows = []
        for _, row in df.iterrows():
            trade_date = row['日期'] # string YYYY-MM-DD
            rows.append((
                std_code,
                trade_date,
                float(row['开盘']),
                float(row['最高']),
                float(row['最低']),
                float(row['收盘']),
                0.0, # pre_close (not easy to get, maybe calc from prev close?)
                int(row['成交量']),
                float(row['成交额']),
                float(row['换手率']) if '换手率' in row else 0,
                float(row['涨跌幅']) if '涨跌幅' in row else 0,
                1 # trade_status
            ))
            
        if not rows:
            return

        # Insert
        sql = """
        INSERT INTO stock_kline_daily 
            (code, trade_date, open, high, low, close, pre_close, volume, amount, turnover, pct_chg, trade_status)
        VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            open=VALUES(open), high=VALUES(high), low=VALUES(low), close=VALUES(close),
            volume=VALUES(volume), amount=VALUES(amount),
            turnover=VALUES(turnover), pct_chg=VALUES(pct_chg)
        """
        await db.execute_many(sql, rows)

