from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.logger import get_logger
import datetime

logger = get_logger("gateway.kline_service")

class KlineService:
    """K 线数据服务"""
    
    async def get_kline(
        self, 
        code: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None, 
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """获取日 K 线数据"""
        try:
            # 标准化代码格式: 确保为 600519.SH (大写)
            if "." in code:
                parts = code.split(".")
                # 如果是 sh.600519 格式，转换为 600519.SH
                if len(parts[0]) == 2 and parts[0].isalpha():
                    code = f"{parts[1]}.{parts[0].upper()}"
                else:
                    code = code.upper()
            elif code.isdigit():
                # 处理纯数字，尝试补全后缀 (简单逻辑)
                if code.startswith(('6', '9')):
                    code = f"{code}.SH"
                else:
                    code = f"{code}.SZ"
            
            sql = "SELECT trade_date, open, high, low, close, volume, amount, turnover FROM stock_kline_daily WHERE code = %s"
            params = [code]
            
            if start_date:
                sql += " AND trade_date >= %s"
                params.append(start_date)
            
            if end_date:
                sql += " AND trade_date <= %s"
                params.append(end_date)
            
            sql += " ORDER BY trade_date DESC LIMIT %s"
            params.append(limit)
            
            rows = await db.execute(sql, tuple(params))
            
            results = []
            # 注意：返回结果是倒序的（最新的在前），前端通常需要正序
            for row in reversed(rows):
                results.append({
                    "date": row[0].strftime("%Y-%m-%d") if isinstance(row[0], (datetime.date, datetime.datetime)) else str(row[0]),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                    "amount": float(row[6]),
                    "turnover": float(row[7]) if row[7] is not None else None
                })
            
            return results
        except Exception as e:
            logger.error(f"获取 K 线数据失败: {e}")
            raise e

kline_service = KlineService()
