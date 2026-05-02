from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any, List
from app.utils.database import db
from app.utils.http_client import http_client
from app.utils.logger import get_logger

logger = get_logger("stock-manager.suspension")

class SuspensionService:
    """股票停牌数据服务"""
    
    # P0-3: 移除内联 DDL，已迁移至 /database/migrations/ 管理

    async def fetch_market_status(self, date: str) -> List[Dict[str, Any]]:
        """从 BaoStock-API 获取全市场状态"""
        try:
            # 调用我们在 baostock-api 新增的接口
            path = "/api/v1/market/stocks"
            params = {"date": date}
            data = await http_client.get("baostock", path, params=params)
            return data
        except Exception as e:
            logger.error(f"从 BaoStock 获取市场状态失败 ({date}): {e}")
            return []

    async def save_suspensions(self, date: str, stocks: List[Dict[str, Any]]) -> int:
        """保存停牌数据"""
        if not stocks:
            return 0
        
        # 筛选出停牌的股票 (trade_status=0)
        suspended_stocks = [s for s in stocks if s.get("trade_status") == 0]
        
        if not suspended_stocks:
            logger.info(f"日期 {date} 无停牌股票")
            return 0
            
        sql = """
        INSERT INTO stock_suspensions 
        (ts_code, trade_date, is_suspended)
        VALUES (%s, %s, 1)
        ON DUPLICATE KEY UPDATE
            is_suspended=1,
            updated_at=CURRENT_TIMESTAMP
        """
        
        rows = []
        for s in suspended_stocks:
            rows.append((s["code"], date))
            
        try:
            await db.execute_many(sql, rows)
            logger.info(f"日期 {date} 保存停牌记录: {len(rows)} 条")
            return len(rows)
        except Exception as e:
            logger.error(f"保存停牌记录失败 ({date}): {e}")
            raise

    async def sync_date_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """同步指定日期范围的停牌数据"""
        # await self.create_table_if_not_exists() # P0-3 移除
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        current = start
        stats = {"total_days": 0, "processed_days": 0, "total_records": 0, "errors": []}
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            # 跳过周末 (简单判断) - BaoStock API 会处理非交易日(返回空或报错)，但为了效率我们可以跳过周末
            if current.weekday() < 5: 
                try:
                    stocks = await self.fetch_market_status(date_str)
                    if stocks:
                        count = await self.save_suspensions(date_str, stocks)
                        stats["total_records"] += count
                    stats["processed_days"] += 1
                except Exception as e:
                    stats["errors"].append(f"{date_str}: {str(e)}")
            
            current += timedelta(days=1)
            stats["total_days"] += 1
            
            # 简单节流
            await asyncio.sleep(0.1)
            
        return stats
    async def sync_today_suspensions(self) -> int:
        """从 AkShare 同步今日停牌数据 (早盘任务)"""
        # await self.create_table_if_not_exists() # P0-3 移除
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"开始执行早盘停牌数据同步: {today_str}")
        
        try:
            # 1. 从 akshare-api 获取数据 (stock_tfp_em)
            path = "/api/v1/suspension/daily"
            params = {"date": today_str}
            data = await http_client.get("akshare", path, params=params)
            
            if not data:
                logger.info(f"今日 ({today_str}) AkShare 未返回停牌数据")
                return 0
                
            # 2. 格式化数据
            rows = []
            for item in data:
                # 兼容不同数据源返回的 code 格式
                code = item.get("code", "")
                
                # 统一转换为标准格式 (Suffix: XXXXXX.SZ/SH/BJ)
                if code.startswith(("sh.", "sz.", "bj.")):
                    # 如果是前缀格式 (sz.000001)，转为后缀
                    parts = code.split(".")
                    code = f"{parts[1]}.{parts[0].upper()}"
                elif "." in code:
                     # 已经是后缀或其他带点格式，简单大写
                     code = code.upper()
                else:
                    # 纯数字，需要手动推断
                     if code.startswith("6"): 
                         code = f"{code}.SH"
                     elif code.startswith("8") or code.startswith("4") or code.startswith("9"): 
                         code = f"{code}.BJ"
                     elif code.startswith("0") or code.startswith("3"): 
                         code = f"{code}.SZ"
                     else:
                         # 兜底默认 SZ，或者记录 warning
                         code = f"{code}.SZ"
                
                reason = item.get("reason", "")
                rows.append((code, today_str, 1, reason))
                
            # 3. 保存
            sql = """
            INSERT INTO stock_suspensions 
            (ts_code, trade_date, is_suspended, reason)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                is_suspended=VALUES(is_suspended),
                reason=VALUES(reason),
                updated_at=CURRENT_TIMESTAMP
            """
            
            await db.execute_many(sql, rows)
            logger.info(f"今日 ({today_str}) 早盘停牌数据同步完成: {len(rows)} 条")
            return len(rows)
            
        except Exception as e:
            logger.error(f"早盘停牌数据同步失败: {e}")
            raise
