import datetime
from typing import Dict, Any, List
from app.utils.database import db
from app.utils.logger import get_logger
from app.services.baseline_service import BaselineService

logger = get_logger("stock-manager.dq_metrics")


class DQMetricsService:
    """数据质量指标服务 (E7)"""

    def __init__(self):
        self.baseline_service = BaselineService()

    async def calculate_daily_metrics(
            self, target_date: str) -> Dict[str, float]:
        """计算并存储指定日期的 DQ 指标"""
        try:
            logger.info(f"开始计算日期 {target_date} 的 DQ 指标...")

            # 1. 完整性 (Completeness)
            # 实际记录数 / 基线记录数
            baseline = await self.baseline_service.get_current_baseline()
            total_baseline = baseline.get("total", 5422)

            sql_actual = "SELECT COUNT(DISTINCT ts_code) FROM stock_kline_daily WHERE trade_date = %s"
            res_actual = await db.execute(sql_actual, (target_date,))
            actual_count = res_actual[0][0] if res_actual else 0

            completeness = (
                actual_count /
                total_baseline) if total_baseline > 0 else 0

            # 2. 一致性 (Consistency)
            # 一致率 = 1 - (比对失败数 / 基线总数)
            sql_consistency_issues = """
                SELECT COUNT(DISTINCT ts_code) FROM dq_findings
                WHERE trade_date = %s AND rule_id = 'cross_source'
            """
            res_consistency = await db.execute(sql_consistency_issues, (target_date,))
            consistency_issues = res_consistency[0][0] if res_consistency else 0
            consistency = max(0, 1 - (consistency_issues /
                              total_baseline)) if total_baseline > 0 else 1.0

            # 3. 准确性 (Accuracy)
            # 准确率 = 1 - (校验失败数 / 基线总数)
            sql_accuracy_issues = """
                SELECT COUNT(DISTINCT ts_code) FROM dq_findings
                WHERE trade_date = %s AND rule_id = 'business_rule'
            """
            res_accuracy = await db.execute(sql_accuracy_issues, (target_date,))
            accuracy_issues = res_accuracy[0][0] if res_accuracy else 0
            accuracy = max(0, 1 - (accuracy_issues / total_baseline)
                           ) if total_baseline > 0 else 1.0

            # 4. 及时性 (Timeliness)
            # T+1 数据在 09:00 前完成同步为 100%，否则递减
            sql_timeliness = """
                SELECT finished_at FROM commands
                WHERE task_id = 'daily_kline_sync'
                  AND DATE(created_at) = %s
                  AND status = 'SUCCESS'
                ORDER BY finished_at DESC LIMIT 1
            """
            res_time = await db.execute(sql_timeliness, (target_date,))
            timeliness = 0.0
            if res_time and res_time[0][0]:
                finish_time = res_time[0][0]
                deadline = datetime.datetime.combine(
                    finish_time.date(), datetime.time(9, 0))
                if finish_time <= deadline:
                    timeliness = 1.0
                else:
                    delay_hours = (
                        finish_time - deadline).total_seconds() / 3600
                    timeliness = max(0.5, 1.0 - delay_hours * 0.1)
            else:
                timeliness = 0.0

            metrics = {
                "completeness": float(completeness),
                "consistency": float(consistency),
                "accuracy": float(accuracy),
                "timeliness": float(timeliness)
            }

            # 5. 存储指标
            targets = {
                "completeness": 0.999,
                "consistency": 0.995,
                "accuracy": 1.0,
                "timeliness": 1.0
            }

            for name, value in metrics.items():
                target = targets.get(name, 1.0)
                status = "OK"
                if value < target:
                    status = "WARNING" if value >= target * 0.95 else "ERROR"

                sql_insert = """
                    INSERT INTO dq_metrics_history (trade_date, indicator_name, indicator_value, target_value, status)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        indicator_value = VALUES(indicator_value),
                        target_value = VALUES(target_value),
                        status = VALUES(status)
                """
                await db.execute(sql_insert, (target_date, name, value, target, status))

            logger.info(f"日期 {target_date} DQ 指标计算完成: {metrics}")
            return metrics
        except Exception as e:
            logger.error(f"计算 DQ 指标失败: {e}")
            raise e


dq_metrics_service = DQMetricsService()
