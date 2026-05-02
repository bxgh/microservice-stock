import datetime
from typing import Dict, Any
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("stock-manager.ops")

class OpsService:
    """运维服务"""
    
    async def get_sync_freshness(self) -> Dict[str, Any]:
        """获取数据时效性指标"""
        try:
            sql = "SELECT MAX(created_at) FROM stock_kline_daily"
            res = await db.execute(sql)
            last_sync_time = res[0][0] if res and res[0][0] else None
            
            if not last_sync_time:
                return {"lastSyncTime": None, "lagMinutes": -1, "status": "critical"}
            
            now = datetime.datetime.now()
            lag = int((now - last_sync_time).total_seconds() / 60)
            status = "normal" if lag <= 30 else ("warning" if lag <= 120 else "critical")
            
            return {
                "lastSyncTime": last_sync_time.strftime("%Y-%m-%d %H:%M:%S"),
                "lagMinutes": lag,
                "status": status
            }
        except Exception as e:
            logger.error(f"Freshness check 异常: {e}")
            return {"error": str(e)}

    async def get_adjust_factor_by_date(self, date: str = None) -> Dict[str, Any]:
        """获取指定日期的复权因子数据"""
        try:
            # 如果没有指定日期，使用今天
            if not date:
                date = datetime.date.today().strftime("%Y-%m-%d")
            
            # 查询指定日期的复权因子数量
            sql = "SELECT COUNT(DISTINCT ts_code) FROM stock_adjust_factor WHERE adjust_date = %s"
            res = await db.execute(sql, (date,))
            count = res[0][0] if res and res[0] else 0
            
            # 获取部分股票代码示例
            sql_codes = "SELECT DISTINCT ts_code FROM stock_adjust_factor WHERE adjust_date = %s LIMIT 10"
            codes_res = await db.execute(sql_codes, (date,))
            codes = [row[0] for row in codes_res] if codes_res else []
            
            return {
                "date": date,
                "count": count,
                "codes": codes
            }
        except Exception as e:
            logger.error(f"获取复权因子数据异常: {e}")
            return {"date": date, "count": 0, "error": str(e)}
    async def remediate_data(self, date: str, data_type: str = "kline", scope: str = "incremental") -> Dict[str, Any]:
        """触发指定日期的数据补偿
        
        Args:
            date: 日期 YYYY-MM-DD
            data_type: 数据类型，目前仅支持 kline
            scope: 范围 incremental/full
        """
        from app.utils.http_client import http_client
        try:
            params = {
                "date": date,
                "dataType": data_type,
                "scope": scope
            }
            result = await http_client.post(
                "baostock",
                "/api/v1/sync/remediate",
                params=params
            )
            return result
        except Exception as e:
            logger.error(f"触发补偿任务失败: {e}")
            return {"status": "error", "message": str(e)}
