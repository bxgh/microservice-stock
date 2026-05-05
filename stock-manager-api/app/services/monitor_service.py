from typing import List, Optional, Dict, Any
from app.utils.database import db
from app.utils.logger import get_logger
from app.schemas.monitor import MonitorSummary, IndicatorItem, HistoryPoint

logger = get_logger("stock-manager.monitor_service")


class MonitorService:
    async def get_summary(self) -> Optional[MonitorSummary]:
        """获取最新一天的监控汇总"""
        try:
            # 1. 获取最新健康分
            sql_health = "SELECT trade_date, total_score, status FROM monitor_health_scores ORDER BY trade_date DESC LIMIT 1"
            health_rows = await db.execute(sql_health)
            if not health_rows:
                return None

            target_date, total_score, status = health_rows[0]

            # 2. 获取该日期的各项指标
            sql_indicators = """
                SELECT indicator_name, indicator_value, score
                FROM monitor_indicators_history
                WHERE trade_date = %s
            """
            indicator_rows = await db.execute(sql_indicators, (target_date,))

            indicators = []
            for name, val, score in indicator_rows:
                indicators.append(IndicatorItem(
                    name=name,
                    value=val,
                    score=score
                ))

            return MonitorSummary(
                trade_date=target_date,
                total_score=total_score,
                status=status,
                indicators=indicators
            )
        except Exception as e:
            logger.error(f"获取监控汇总失败: {e}")
            raise

    async def get_score_history(self, limit: int = 90) -> List[HistoryPoint]:
        """获取健康分历史趋势"""
        try:
            sql = "SELECT trade_date, total_score FROM monitor_health_scores ORDER BY trade_date DESC LIMIT %s"
            rows = await db.execute(sql, (limit,))

            # 翻转逻辑以便图表从左到右显示
            return [HistoryPoint(trade_date=r[0], value=r[1])
                    for r in reversed(rows)]
        except Exception as e:
            logger.error(f"获取健康分历史失败: {e}")
            raise

    async def get_indicator_history(
            self,
            name: str,
            limit: int = 90) -> List[HistoryPoint]:
        """获取单个指标的历史趋势"""
        try:
            sql = """
                SELECT trade_date, indicator_value
                FROM monitor_indicators_history
                WHERE indicator_name = %s
                ORDER BY trade_date DESC LIMIT %s
            """
            rows = await db.execute(sql, (name, limit))
            return [HistoryPoint(trade_date=r[0], value=r[1])
                    for r in reversed(rows)]
        except Exception as e:
            logger.error(f"获取指标历史失败 ({name}): {e}")
            raise
