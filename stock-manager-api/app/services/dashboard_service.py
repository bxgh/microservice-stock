import datetime
from typing import Dict, Any, List
from app.utils.database import db
from app.utils.logger import get_logger
from app.services.baseline_service import BaselineService
from app.services.ops_service import OpsService

logger = get_logger("stock-manager.dashboard")

class DashboardService:
    def __init__(self):
        self.baseline_service = BaselineService()
        self.ops_service = OpsService()

    async def get_overview(self) -> Dict[str, Any]:
        """获取今日数据概览"""
        try:
            # 1. 获取基线总数
            baseline = await self.baseline_service.get_current_baseline()
            total_stocks = baseline.get("total", 0)

            # 2. 获取最新K线同步数
            sql_latest_date = "SELECT MAX(trade_date) FROM stock_kline_daily"
            date_res = await db.execute(sql_latest_date)
            latest_date = date_res[0][0] if date_res and date_res[0][0] else None

            kline_count = 0
            if latest_date:
                # K线更新统计
                sql_kline_count = "SELECT COUNT(DISTINCT ts_code) FROM stock_kline_daily WHERE trade_date = %s"
                count_res = await db.execute(sql_kline_count, (latest_date,))
                kline_count = count_res[0][0] if count_res and count_res[0] else 0

            kline_coverage = round((kline_count / total_stocks) * 100, 1) if total_stocks > 0 else 0
            
            # 3. 实时查询 tick 覆盖率 (目前暂无 tick 表，返回 0)
            tick_coverage = 0.0
            
            # 4. 获取最近任务
            recent_tasks = await self._get_recent_tasks()

            return {
                "date": datetime.date.today().strftime("%Y-%m-%d"),
                "kline_coverage": kline_coverage,
                "tick_coverage": tick_coverage,
                "kline_status": "ok" if kline_coverage > 95 else "warning",
                "tick_status": "warning",
                "recent_tasks": recent_tasks
            }
        except Exception as e:
            logger.error(f"获取概览失败: {e}")
            raise

    async def _get_recent_tasks(self) -> List[Dict[str, Any]]:
        """从 commands 表获取最近触发的任务"""
        try:
            sql = """
            SELECT task_id, status, created_at 
            FROM commands 
            ORDER BY created_at DESC 
            LIMIT 5
            """
            rows = await db.execute(sql)
            tasks = []
            task_name_map = {
                "daily_kline_sync": "K线同步",
                "sync_tick": "分笔采集",
                "pre_market_gate": "盘前校验"
            }
            for row in rows:
                tasks.append({
                    "task_id": row[0],
                    "name": task_name_map.get(row[0], row[0]),
                    "status": row[1],
                    "last_run": row[2].strftime("%Y-%m-%dT%H:%M:%S") if row[2] else None
                })
            return tasks
        except Exception as e:
            logger.warning(f"获取最近任务失败: {e}")
            return []
