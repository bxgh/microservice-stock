import bisect
import datetime
from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("gateway.kline_service")

class KlineService:
    """K 线数据服务"""
    
    async def _get_adjust_factors(self, code: str) -> List[Dict[str, Any]]:
        """获取复权因子"""
        try:
            sql = "SELECT adjust_date, fore_adjust_factor FROM stock_adjust_factor WHERE ts_code = %s ORDER BY adjust_date ASC"
            rows = await db.execute(sql, (code,))
            return [{"date": str(row["adjust_date"]), "factor": float(row["fore_adjust_factor"])} for row in rows]
        except Exception as e:
            logger.warning(f"获取复权因子失败: {e}")
            return []

    async def get_kline(
        self, 
        code: str, 
        frequency: str = "d",
        adjust: str = "2",  # 2: 前复权 (默认), 1: 后复权, 3: 不复权
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None, 
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """获取 K 线数据，支持复权与聚合"""
        try:
            # 标准化代码格式
            if "." in code:
                parts = code.split(".")
                if len(parts[0]) == 2 and parts[0].isalpha():
                    code = f"{parts[1]}.{parts[0].upper()}"
                else:
                    code = code.upper()
            elif code.isdigit():
                if code.startswith(('6', '9')):
                    code = f"{code}.SH"
                else:
                    code = f"{code}.SZ"
            
            # 1. 确定获取原始数据的数量
            fetch_limit = limit
            if frequency == "w":
                fetch_limit = limit * 5 + 10
            elif frequency == "m":
                fetch_limit = limit * 22 + 40
            elif frequency == "y":
                fetch_limit = limit * 252 + 500
            
            fetch_limit = min(fetch_limit, 5000)

            # 2. 查询原始日线数据
            sql = """
                SELECT trade_date, open, high, low, close, pre_close, volume, amount, turnover, pct_chg, trade_status 
                FROM stock_kline_daily 
                WHERE ts_code = %s
            """
            params = [code]
            if start_date:
                sql += " AND trade_date >= %s"
                params.append(start_date)
            if end_date:
                sql += " AND trade_date <= %s"
                params.append(end_date)
            
            sql += " ORDER BY trade_date DESC LIMIT %s"
            params.append(fetch_limit)
            
            rows = await db.execute(sql, tuple(params))
            if not rows:
                return []
            
            # 转换为正序处理
            raw_data = []
            for row in reversed(rows):
                raw_data.append({
                    "date": str(row["trade_date"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "pre_close": float(row["pre_close"]) if row["pre_close"] is not None else None,
                    "volume": float(row["volume"]),
                    "amount": float(row["amount"]),
                    "turnover": float(row["turnover"]) if row["turnover"] is not None else None,
                    "pct_chg": float(row["pct_chg"]) if row["pct_chg"] is not None else None,
                    "trade_status": int(row["trade_status"]) if row["trade_status"] is not None else None
                })

            # 3. 处理复权
            if adjust in ["1", "2"] and raw_data:
                factors = await self._get_adjust_factors(code)
                if factors:
                    self._apply_adjustment(raw_data, factors, adjust)

            # 4. 处理聚合 (周/月/年)
            if frequency in ["w", "m", "y"]:
                result = self._aggregate_data(raw_data, frequency)
            else:
                result = raw_data
            
            # 5. 截取最终需要的条数
            return result[-limit:]
            
        except Exception as e:
            logger.error(f"获取 K 线数据失败: {e}", exc_info=True)
            raise e

    def _apply_adjustment(self, data: List[Dict], factors: List[Dict], adjust_type: str):
        """应用复权计算"""
        factor_dates = [f["date"] for f in factors]
        
        for item in data:
            idx = bisect.bisect_right(factor_dates, item["date"]) - 1
            if idx >= 0:
                f = factors[idx]["factor"]
                for field in ["open", "high", "low", "close", "pre_close"]:
                    if item[field] is not None:
                        item[field] = round(item[field] * f, 3)

    def _aggregate_data(self, data: List[Dict], freq: str) -> List[Dict]:
        """聚合日线数据为周线或月线"""
        if not data:
            return []
            
        aggregated = []
        current_group = []
        last_key = None
        
        for item in data:
            dt = datetime.datetime.strptime(item["date"], "%Y-%m-%d")
            if freq == "w":
                year, week, _ = dt.isocalendar()
                key = f"{year}-{week:02d}"
            elif freq == "m":
                key = f"{dt.year}-{dt.month:02d}"
            else: # freq == "y"
                key = f"{dt.year}"
            
            if key != last_key and current_group:
                aggregated.append(self._reduce_group(current_group))
                current_group = []
            
            current_group.append(item)
            last_key = key
            
        if current_group:
            aggregated.append(self._reduce_group(current_group))
            
        return aggregated

    def _reduce_group(self, group: List[Dict]) -> Dict:
        """合并一组数据"""
        first = group[0]
        last = group[-1]
        return {
            "date": last["date"],
            "open": first["open"],
            "high": max(item["high"] for item in group),
            "low": min(item["low"] for item in group),
            "close": last["close"],
            "pre_close": first["pre_close"],
            "volume": sum(item["volume"] for item in group),
            "amount": sum(item["amount"] for item in group),
            "turnover": sum(item["turnover"] for item in group) if all(i["turnover"] is not None for i in group) else None,
            "pct_chg": round((last["close"] - first["pre_close"]) / first["pre_close"] * 100, 2) if first["pre_close"] else None,
            "trade_status": last["trade_status"]
        }

kline_service = KlineService()
