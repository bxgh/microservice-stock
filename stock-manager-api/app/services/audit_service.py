import datetime
from typing import Dict, Any
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("stock-manager.audit")

class AuditService:
    """审计服务"""
    
    async def get_audit_weekly(self, week: str = "current") -> Dict[str, Any]:
        """获取周度审计报告"""
        try:
            if week == "current":
                today = datetime.date.today()
                start_date = today - datetime.timedelta(days=today.weekday())
                week_label = today.strftime("%Y-W%V")
            else:
                try:
                    year_part, week_part = week.split("-W")
                    start_date = datetime.datetime.strptime(f"{year_part}-W{week_part}-1", "%G-W%V-%u").date()
                    week_label = week
                except:
                    raise ValueError("Invalid week format")
            
            end_date = start_date + datetime.timedelta(days=6)
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # 获取交易日历
            sql_cal = "SELECT cal_date, is_open FROM trade_cal WHERE cal_date BETWEEN %s AND %s"
            cal_rows = await db.execute(sql_cal, (start_str, end_str))
            
            # 获取基线：使用最近一个交易日的实际股票数作为基准
            # 这样可以避免代码格式不一致的问题
            sql_baseline = """
                SELECT COUNT(DISTINCT code) 
                FROM stock_kline_daily 
                WHERE trade_date = (
                    SELECT MAX(trade_date) 
                    FROM stock_kline_daily 
                    WHERE trade_date < %s
                )
            """
            baseline_res = await db.execute(sql_baseline, (start_str,))
            total_baseline = baseline_res[0][0] if baseline_res else 5422
            
            # 如果查不到，使用静态基线
            if not total_baseline:
                total_baseline = 5422
                logger.warning(f"无法从K线表获取基线，使用静态值: {total_baseline}")
            
            # 获取 MySQL K线计数
            sql_mysql = "SELECT trade_date, COUNT(DISTINCT code) as count FROM stock_kline_daily WHERE trade_date BETWEEN %s AND %s GROUP BY trade_date"
            mysql_res = await db.execute(sql_mysql, (start_str, end_str))
            mysql_counts = {
                row[0].strftime("%Y-%m-%d") if isinstance(row[0], (datetime.date, datetime.datetime)) else str(row[0]): row[1]
                for row in mysql_res
            }
            

            # 获取 ClickHouse 验证记录（从数据质量报告表获取真实 Actual）
            sql_dq = """
                SELECT report_content 
                FROM data_quality_reports 
                WHERE report_type = 'daily' 
                  AND check_time >= %s
                ORDER BY check_time ASC
            """
            dq_res = await db.execute(sql_dq, (start_str,))
            
            # 处理质量报告数据
            import json
            ch_counts = {}
            for row in dq_res:
                try:
                    content = json.loads(row[0])
                    checks = content.get('checks', {})
                    
                    # 格式1: daily_completeness (单日报告)
                    comp = checks.get('daily_completeness', {})
                    biz_date = comp.get('date')
                    actual = comp.get('actual')
                    if biz_date and actual is not None:
                        ch_counts[biz_date] = actual
                        
                    # 格式2: cross_db_consistency (多日对齐报告)
                    cross = checks.get('cross_db_consistency', {})
                    details = cross.get('details', [])
                    for item in details:
                        b_date = item.get('date')
                        ch_val = item.get('clickhouse_count')
                        if b_date and ch_val is not None:
                            ch_counts[b_date] = ch_val
                            
                except Exception as e:
                    logger.warning(f"解析质量报告失败: {e}")
            
            # 组装数据
            days = []
            for cal_row in cal_rows:
                d_date = cal_row[0].strftime("%Y-%m-%d") if isinstance(cal_row[0], (datetime.date, datetime.datetime)) else str(cal_row[0])
                is_open = int(cal_row[1])
                
                if not is_open:
                    days.append({"date": d_date, "overallStatus": "holiday"})
                    continue
                
                l2_mysql = mysql_counts.get(d_date, 0)
                l3_ch = ch_counts.get(d_date, 0)
                
                # 完整性计算：对比 L2 (云端) 与 L3 (内网) 的一致性
                # 审计目标是确保“同步到了内网”，所以 Pct = L3 / L2 是最直接的质量指标
                # 但由于业务关心相对于总体的完整性，我们计算 (L3 / Baseline) 并限制最大为 100%
                raw_pct = (l3_ch / total_baseline * 100) if total_baseline > 0 else 0
                pct = round(min(100.0, raw_pct), 2)
                
                # 状态判定
                if pct >= 100:
                    status = "complete"
                elif pct >= 95:
                    status = "partial"
                else:
                    status = "critical"
                
                days.append({
                    "date": d_date,
                    "kline": {
                        "l1_baseline": total_baseline,
                        "l2_mysql": l2_mysql,
                        "l3_clickhouse": l3_ch,
                        "completeness_pct": pct
                    },
                    "overallStatus": status
                })
            
            return {
                "weekLabel": week_label,
                "lastUpdated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "days": days
            }
        except Exception as e:
            logger.error(f"Audit weekly 异常: {e}")
            return {"error": str(e)}

    async def get_gate_audits(self, trade_date: str = None, limit: int = 50) -> Dict[str, Any]:
        """获取数据闸门审计记录"""
        try:
            params = []
            sql = "SELECT id, trade_date, gate_id, is_complete, description, created_at FROM data_gate_audits WHERE 1=1"
            
            if trade_date:
                sql += " AND trade_date = %s"
                params.append(trade_date)
            
            sql += " ORDER BY trade_date DESC, created_at DESC LIMIT %s"
            params.append(limit)
            
            rows = await db.execute(sql, tuple(params))
            
            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "trade_date": row[1].strftime("%Y-%m-%d") if row[1] else None,
                    "gate_id": row[2],
                    "is_complete": bool(row[3]),
                    "description": row[4],
                    "created_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else None
                })
            
            return {"audits": results}
        except Exception as e:
            logger.error(f"Get gate audits 异常: {e}")
            raise e
